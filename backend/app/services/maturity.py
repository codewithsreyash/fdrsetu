"""Smart Maturity & Renewal: computes upcoming expiries and raises notifications."""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ..models import FDRRecord, FDRStatus, Notification, Institution, User, Role

ALERT_WINDOWS = (90, 60, 30)


def run_maturity_scan(db: Session) -> dict:
    """Update expired statuses and create 90/60/30-day maturity notifications."""
    today = date.today()
    stats = {"expired_marked": 0, "notifications_created": 0, "windows": {}}

    fdrs = db.query(FDRRecord).filter(
        FDRRecord.status.in_([FDRStatus.pending, FDRStatus.active, FDRStatus.verified])
    ).all()

    for fdr in fdrs:
        if fdr.maturity_date < today:
            fdr.status = FDRStatus.expired
            stats["expired_marked"] += 1
            continue
        days = (fdr.maturity_date - today).days
        for window in ALERT_WINDOWS:
            if days <= window and days > (window - 30 if window != 30 else -1):
                stats["windows"][window] = stats["windows"].get(window, 0) + 1
                # dedupe via unique constraint on (kind, message)
                inst = db.get(Institution, fdr.institution_id)
                msg = (f"FDR {fdr.fdr_uid} ({fdr.fdr_number}) of {inst.name if inst else ''} "
                       f"matures on {fdr.maturity_date} ({days} days left).")
                for role in (Role.institution, Role.officer):
                    exists = db.query(Notification).filter(
                        Notification.kind == "maturity", Notification.message == msg,
                        Notification.role == role.value,
                    ).first()
                    if exists:
                        continue
                    db.add(Notification(
                        role=role.value,
                        institution_id=fdr.institution_id if role == Role.institution else None,
                        title=f"Maturity alert — {days} days",
                        message=msg, kind="maturity",
                    ))
                    stats["notifications_created"] += 1
                break
    db.commit()
    return stats


def upcoming_maturities(db: Session, days: int = 90):
    today = date.today()
    return db.query(FDRRecord).filter(
        FDRRecord.maturity_date >= today,
        FDRRecord.maturity_date <= today + timedelta(days=days),
        FDRRecord.status.in_([FDRStatus.pending, FDRStatus.active, FDRStatus.verified]),
    ).order_by(FDRRecord.maturity_date).all()


def expired_fdrs(db: Session):
    today = date.today()
    return db.query(FDRRecord).filter(
        (FDRRecord.maturity_date < today) &
        (FDRRecord.status != FDRStatus.released)
    ).order_by(FDRRecord.maturity_date).all()
