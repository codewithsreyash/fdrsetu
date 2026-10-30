from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    FDRRecord, FDRStatus, VerificationStatus, RiskLevel, RiskAlert,
    ReleaseRequest, ReleaseStatus, RenewalRecord, Institution, Bank, User, Role,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _scope(user: User, q):
    if user.role == Role.institution:
        return q.filter(FDRRecord.institution_id == user.institution_id)
    if user.role == Role.bank:
        return q.filter(FDRRecord.bank_id == user.bank_id)
    return q


@router.get("/kpis")
def kpis(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    base = _scope(user, db.query(FDRRecord))

    def count(q):
        return q.count() if hasattr(q, "count") else q.scalar()

    total = base.count()
    active = base.filter(FDRRecord.status.in_([FDRStatus.active, FDRStatus.verified])).count()
    pending_verif = base.filter(
        FDRRecord.verification_status.in_([VerificationStatus.pending, VerificationStatus.in_review])).count()
    verified = base.filter(FDRRecord.verification_status == VerificationStatus.verified).count()
    upcoming = base.filter(FDRRecord.maturity_date >= today,
                           FDRRecord.maturity_date <= today + timedelta(days=90)).count()
    expired = base.filter(FDRRecord.maturity_date < today,
                          FDRRecord.status != FDRStatus.released).count()
    high_risk = base.filter(FDRRecord.risk_level == RiskLevel.high).count()
    released = base.filter(FDRRecord.status == FDRStatus.released).count()
    total_amount = base.with_entities(func.coalesce(func.sum(FDRRecord.amount), 0)).scalar()

    rq = db.query(ReleaseRequest)
    if user.role == Role.institution:
        rq = rq.filter(ReleaseRequest.institution_id == user.institution_id)
    release_pending = rq.filter(ReleaseRequest.status.in_(
        [ReleaseStatus.pending, ReleaseStatus.under_review])).count()
    renewal_pending = db.query(RenewalRecord).filter(
        RenewalRecord.status.in_(["pending", "submitted"])).count()
    institutions = db.query(func.count(Institution.id)).scalar()

    return {
        "institutions": institutions,
        "total_fdrs": total, "active_fdrs": active,
        "pending_verification": pending_verif, "verified_fdrs": verified,
        "upcoming_maturity_90d": upcoming, "expired_fdrs": expired,
        "renewal_pending": renewal_pending, "release_pending": release_pending,
        "high_risk": high_risk, "released_fdrs": released,
        "total_amount": float(total_amount or 0),
    }


@router.get("/charts")
def charts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = _scope(user, db.query(FDRRecord))

    inst_rows = base.join(Institution, FDRRecord.institution_id == Institution.id) \
        .with_entities(Institution.name, func.count(FDRRecord.id)) \
        .group_by(Institution.name).order_by(func.count(FDRRecord.id).desc()).limit(10).all()

    bank_rows = base.join(Bank, FDRRecord.bank_id == Bank.id) \
        .with_entities(Bank.name, func.count(FDRRecord.id)) \
        .group_by(Bank.name).all()

    monthly = base.with_entities(
        extract("year", FDRRecord.issue_date).label("y"),
        extract("month", FDRRecord.issue_date).label("m"),
        func.count(FDRRecord.id)) \
        .group_by("y", "m").order_by("y", "m").all()

    verif_rows = base.with_entities(FDRRecord.verification_status, func.count(FDRRecord.id)) \
        .group_by(FDRRecord.verification_status).all()

    today = date.today()
    buckets = {"0-30 days": 0, "31-60 days": 0, "61-90 days": 0, "90+ days": 0}
    for (md,) in base.filter(FDRRecord.maturity_date >= today,
                             FDRRecord.status != FDRStatus.released) \
                     .with_entities(FDRRecord.maturity_date).all():
        d = (md - today).days
        buckets["0-30 days" if d <= 30 else "31-60 days" if d <= 60 else
                "61-90 days" if d <= 90 else "90+ days"] += 1

    rel_rows = db.query(ReleaseRequest.status, func.count(ReleaseRequest.id)) \
        .group_by(ReleaseRequest.status).all()

    return {
        "institution_distribution": [{"name": n, "count": c} for n, c in inst_rows],
        "bank_distribution": [{"name": n, "count": c} for n, c in bank_rows],
        "monthly_submissions": [{"month": f"{int(y)}-{int(m):02d}", "count": c}
                                for y, m, c in monthly],
        "verification_status": [{"name": s.value, "count": c} for s, c in verif_rows],
        "maturity_buckets": [{"name": k, "count": v} for k, v in buckets.items()],
        "release_status": [{"name": s.value, "count": c} for s, c in rel_rows],
    }
