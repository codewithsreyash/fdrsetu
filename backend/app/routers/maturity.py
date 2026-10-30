from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import (
    FDRRecord, FDRStatus, RenewalRecord, Institution, User, Role, Notification,
)
from ..services.maturity import run_maturity_scan, upcoming_maturities, expired_fdrs
from .fdrs import fdr_out

router = APIRouter(prefix="/maturity", tags=["maturity"])


@router.post("/scan")
def scan(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Run the 90/60/30-day maturity scan (also runs at startup)."""
    stats = run_maturity_scan(db)
    audit(db, user, "maturity_scan", "fdr", None, str(stats))
    db.commit()
    return stats


@router.get("/upcoming")
def upcoming(days: int = 90, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    rows = upcoming_maturities(db, days)
    if user.role == Role.institution:
        rows = [f for f in rows if f.institution_id == user.institution_id]
    elif user.role == Role.bank:
        rows = [f for f in rows if f.bank_id == user.bank_id]
    return [{"days_left": (f.maturity_date - date.today()).days, **fdr_out(f)} for f in rows]


@router.get("/expired")
def expired(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = expired_fdrs(db)
    if user.role == Role.institution:
        rows = [f for f in rows if f.institution_id == user.institution_id]
    elif user.role == Role.bank:
        rows = [f for f in rows if f.bank_id == user.bank_id]
    return [{"days_overdue": (date.today() - f.maturity_date).days, **fdr_out(f)} for f in rows]


@router.get("/renewals")
def list_renewals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(RenewalRecord).order_by(RenewalRecord.created_at.desc())
    if user.role == Role.institution:
        q = q.filter(RenewalRecord.institution_id == user.institution_id)
    out = []
    for r in q.all():
        old = db.get(FDRRecord, r.old_fdr_id)
        new = db.get(FDRRecord, r.new_fdr_id) if r.new_fdr_id else None
        inst = db.get(Institution, r.institution_id)
        out.append({"id": r.id, "status": r.status, "remarks": r.remarks,
                    "old_fdr_uid": old.fdr_uid if old else None,
                    "old_fdr_number": old.fdr_number if old else None,
                    "old_maturity": str(old.maturity_date) if old else None,
                    "new_fdr_uid": new.fdr_uid if new else None,
                    "new_fdr_number": new.fdr_number if new else None,
                    "institution": inst.name if inst else None,
                    "created_at": r.created_at.isoformat()})
    return out


class RenewalIn(BaseModel):
    old_fdr_id: int
    remarks: str | None = None


@router.post("/renewals")
def request_renewal(body: RenewalIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    old = db.get(FDRRecord, body.old_fdr_id)
    if not old:
        raise HTTPException(404, "FDR not found")
    if user.role == Role.institution and old.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    if user.role == Role.bank:
        raise HTTPException(403, "Bank officers cannot request renewals")
    existing = db.query(RenewalRecord).filter(
        RenewalRecord.old_fdr_id == old.id,
        RenewalRecord.status.in_(["pending", "submitted"])).first()
    if existing:
        return {"id": existing.id, "status": existing.status, "detail": "Renewal already tracked"}
    r = RenewalRecord(old_fdr_id=old.id, institution_id=old.institution_id,
                      status="pending", remarks=body.remarks)
    db.add(r)
    db.add(Notification(
        role="officer", title="Renewal pending",
        message=f"Renewal tracked for {old.fdr_uid} ({old.fdr_number}) — "
                f"{old.institution.name if old.institution else ''}.",
        kind="maturity"))
    audit(db, user, "request_renewal", "fdr", old.id, old.fdr_uid)
    db.commit()
    return {"id": r.id, "status": r.status}
