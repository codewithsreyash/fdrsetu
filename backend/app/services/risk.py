"""AI Risk & Duplicate Detection.

Runs rule checks when an FDR is created/updated and on demand. Every finding
becomes a RiskAlert with a human-readable reason and a severity. The system
only flags records for review — it never declares an FDR fraudulent.
"""
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import FDRRecord, RiskAlert, RiskLevel, MockBankLedger, FDRStatus


def _add_alert(db: Session, fdr: FDRRecord, alert_type: str,
               severity: RiskLevel, reason: str):
    # avoid duplicate open alerts of the same type for the same FDR
    existing = db.query(RiskAlert).filter(
        RiskAlert.fdr_id == fdr.id,
        RiskAlert.alert_type == alert_type,
        RiskAlert.status == "open",
    ).first()
    if existing:
        existing.reason = reason
        existing.severity = severity
        return
    db.add(RiskAlert(fdr_id=fdr.id, alert_type=alert_type, severity=severity, reason=reason))


def run_risk_checks(db: Session, fdr: FDRRecord) -> list[RiskAlert]:
    """Evaluate one FDR and persist alerts. Returns open alerts for the FDR."""
    # 1. Duplicate FDR number (same number used by >1 record)
    dupes = db.query(FDRRecord).filter(
        FDRRecord.fdr_number == fdr.fdr_number,
        FDRRecord.id != fdr.id,
    ).all()
    for d in dupes:
        if d.institution_id == fdr.institution_id:
            _add_alert(db, fdr, "duplicate_fdr", RiskLevel.high,
                       f"Duplicate FDR number {fdr.fdr_number}: already registered by this "
                       f"institution as {d.fdr_uid} ({d.institution.name if d.institution else ''}).")
        else:
            _add_alert(db, fdr, "duplicate_fdr_cross_institution", RiskLevel.high,
                       f"FDR number {fdr.fdr_number} is also registered by a different institution "
                       f"({d.institution.name if d.institution else d.institution_id}, record {d.fdr_uid}). "
                       "Possible reuse of the same deposit across institutions.")

    # 2. Missing mandatory fields
    missing = []
    for field, label in [("fdr_number", "FDR number"), ("branch", "branch"),
                         ("ifsc", "IFSC"), ("amount", "amount"),
                         ("issue_date", "issue date"), ("maturity_date", "maturity date")]:
        if getattr(fdr, field) in (None, "", 0):
            missing.append(label)
    if missing:
        _add_alert(db, fdr, "missing_fields", RiskLevel.medium,
                   "Missing mandatory fields: " + ", ".join(missing) + ".")

    # 3. Invalid date combinations
    if fdr.issue_date and fdr.maturity_date:
        if fdr.maturity_date <= fdr.issue_date:
            _add_alert(db, fdr, "invalid_dates", RiskLevel.high,
                       f"Maturity date {fdr.maturity_date} is not after issue date {fdr.issue_date}.")
        elif (fdr.maturity_date - fdr.issue_date).days < 30:
            _add_alert(db, fdr, "invalid_dates", RiskLevel.low,
                       "Deposit tenure is under 30 days — unusual for a security deposit FDR.")
    if fdr.issue_date and fdr.issue_date > date.today():
        _add_alert(db, fdr, "invalid_dates", RiskLevel.medium,
                   f"Issue date {fdr.issue_date} is in the future.")

    # 4. Cross-check against the mock bank ledger (verification-side truth)
    ledger = db.query(MockBankLedger).filter(
        MockBankLedger.fdr_number == fdr.fdr_number
    ).first()
    if ledger:
        if fdr.amount and ledger.amount and abs(float(fdr.amount) - float(ledger.amount)) > 0.01:
            _add_alert(db, fdr, "amount_mismatch", RiskLevel.high,
                       f"Amount mismatch: declared ₹{float(fdr.amount):,.2f} vs bank ledger "
                       f"₹{float(ledger.amount):,.2f} for FDR {fdr.fdr_number}.")
        if fdr.ifsc and ledger.ifsc and fdr.ifsc != ledger.ifsc:
            _add_alert(db, fdr, "bank_detail_mismatch", RiskLevel.medium,
                       f"IFSC mismatch: declared {fdr.ifsc} vs bank ledger {ledger.ifsc}.")
        if fdr.maturity_date and ledger.maturity_date and fdr.maturity_date != ledger.maturity_date:
            _add_alert(db, fdr, "bank_detail_mismatch", RiskLevel.medium,
                       f"Maturity date mismatch: declared {fdr.maturity_date} vs bank ledger "
                       f"{ledger.maturity_date}.")
    else:
        _add_alert(db, fdr, "no_bank_record", RiskLevel.low,
                   f"No record of FDR {fdr.fdr_number} in the (mock) bank ledger yet — "
                   "pending bank-side confirmation.")

    # 5. IFSC format sanity
    if fdr.ifsc:
        import re
        if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", fdr.ifsc or ""):
            _add_alert(db, fdr, "suspicious_document", RiskLevel.medium,
                       f"IFSC '{fdr.ifsc}' is not a valid IFSC format — document may be inconsistent.")

    db.flush()
    # recompute the FDR's overall risk level from open alerts
    open_alerts = db.query(RiskAlert).filter(
        RiskAlert.fdr_id == fdr.id, RiskAlert.status == "open").all()
    order = {RiskLevel.high: 3, RiskLevel.medium: 2, RiskLevel.low: 1, RiskLevel.none: 0}
    fdr.risk_level = max((a.severity for a in open_alerts), key=lambda s: order[s],
                         default=RiskLevel.none)
    db.flush()
    return open_alerts


def scan_all(db: Session) -> int:
    """Re-run checks across every FDR. Returns count of open alerts."""
    for fdr in db.query(FDRRecord).all():
        run_risk_checks(db, fdr)
    db.commit()
    return db.query(RiskAlert).filter(RiskAlert.status == "open").count()
