from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import RiskAlert, RiskLevel, FDRRecord, User, Role, Notification
from ..services.risk import run_risk_checks, scan_all

router = APIRouter(prefix="/risk", tags=["risk"])


def alert_out(a: RiskAlert) -> dict:
    return {
        "id": a.id, "fdr_id": a.fdr_id,
        "fdr_uid": a.fdr.fdr_uid if a.fdr else None,
        "fdr_number": a.fdr.fdr_number if a.fdr else None,
        "institution": a.fdr.institution.name if a.fdr and a.fdr.institution else None,
        "alert_type": a.alert_type, "severity": a.severity.value,
        "reason": a.reason, "status": a.status,
        "created_at": a.created_at.isoformat(),
    }


@router.get("/alerts")
def list_alerts(status: str | None = None, severity: str | None = None,
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(RiskAlert).order_by(RiskAlert.created_at.desc())
    if user.role == Role.institution:
        q = q.join(FDRRecord, RiskAlert.fdr_id == FDRRecord.id) \
             .filter(FDRRecord.institution_id == user.institution_id)
    elif user.role == Role.bank:
        q = q.join(FDRRecord, RiskAlert.fdr_id == FDRRecord.id) \
             .filter(FDRRecord.bank_id == user.bank_id)
    if status:
        q = q.filter(RiskAlert.status == status)
    if severity:
        q = q.filter(RiskAlert.severity == severity)
    return [alert_out(a) for a in q.limit(500).all()]


@router.post("/scan")
def rescan(db: Session = Depends(get_db),
           user: User = Depends(require_roles(Role.officer, Role.admin))):
    count = scan_all(db)
    audit(db, user, "risk_scan", "fdr", None, f"{count} open alerts")
    db.commit()
    return {"open_alerts": count}


@router.post("/check/{fdr_id}")
def check_one(fdr_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    fdr = db.get(FDRRecord, fdr_id)
    if not fdr:
        raise HTTPException(404, "FDR not found")
    alerts = run_risk_checks(db, fdr)
    db.commit()
    return {"risk_level": fdr.risk_level.value,
            "alerts": [alert_out(a) for a in alerts]}


class ReviewIn(BaseModel):
    status: str  # reviewed / dismissed
    note: str | None = None


@router.post("/alerts/{alert_id}/review")
def review_alert(alert_id: int, body: ReviewIn, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(Role.officer, Role.admin))):
    a = db.get(RiskAlert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    if body.status not in ("reviewed", "dismissed", "open"):
        raise HTTPException(400, "status must be reviewed|dismissed|open")
    a.status = body.status
    a.reviewed_by_id = user.id
    if body.note:
        a.reason += f" [Officer note: {body.note}]"
    # recompute FDR risk
    run_risk_checks(db, a.fdr)
    audit(db, user, "review_alert", "risk_alert", a.id, body.status)
    db.commit()
    return alert_out(a)
