"""AI FDR Copilot — rule-based assistant answering from live DB records.

If OPENAI_API_KEY is configured, `answer_question` can be extended to call the
LLM; the rule engine below already covers every demo scenario so the copilot is
fully functional offline.
"""
import re
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import (
    FDRRecord, FDRStatus, RiskAlert, RiskLevel, VerificationStatus,
    ReleaseRequest, ReleaseStatus, RenewalRecord, Institution, Bank,
)


def _fdr_line(f: FDRRecord) -> dict:
    return {
        "fdr_uid": f.fdr_uid, "fdr_number": f.fdr_number,
        "institution": f.institution.name if f.institution else None,
        "bank": f.bank.name if f.bank else None,
        "amount": float(f.amount) if f.amount else None,
        "issue_date": str(f.issue_date), "maturity_date": str(f.maturity_date),
        "status": f.status.value, "verification": f.verification_status.value,
        "risk_level": f.risk_level.value,
    }


def answer_question(db: Session, question: str) -> dict:
    q = question.lower().strip()
    today = date.today()

    # --- pending verification ---
    if "pending" in q and ("verif" in q or "unverif" in q):
        rows = db.query(FDRRecord).filter(
            FDRRecord.verification_status == VerificationStatus.pending).all()
        return {"intent": "pending_verification",
                "answer": f"{len(rows)} FDR(s) are pending verification.",
                "rows": [_fdr_line(f) for f in rows]}

    # --- expiring within N days ---
    m = re.search(r"(?:expir|matur)[a-z]*.*?(?:next|within|in)\s*(\d+)\s*day", q)
    if m or "upcoming matur" in q or "matur" in q and "soon" in q:
        days = int(m.group(1)) if m else 90
        rows = db.query(FDRRecord).filter(
            FDRRecord.maturity_date >= today,
            FDRRecord.maturity_date <= today + timedelta(days=days),
            FDRRecord.status != FDRStatus.released,
        ).order_by(FDRRecord.maturity_date).all()
        insts = sorted({f.institution.name for f in rows if f.institution})
        return {"intent": "upcoming_maturity", "days": days,
                "answer": f"{len(rows)} FDR(s) mature within {days} days, across "
                          f"{len(insts)} institution(s).",
                "rows": [_fdr_line(f) for f in rows]}

    # --- high risk ---
    if "high" in q and "risk" in q or "risk" in q and ("record" in q or "fdr" in q or "flag" in q):
        level = RiskLevel.high if "high" in q else None
        qry = db.query(FDRRecord).filter(FDRRecord.risk_level != RiskLevel.none)
        if level:
            qry = qry.filter(FDRRecord.risk_level == level)
        rows = qry.all()
        return {"intent": "risk_records",
                "answer": f"{len(rows)} flagged FDR record(s) found.",
                "rows": [_fdr_line(f) for f in rows]}

    # --- risk alerts / duplicate ---
    if "duplicate" in q or "alert" in q:
        alerts = db.query(RiskAlert).filter(RiskAlert.status == "open").all()
        if "duplicate" in q:
            alerts = [a for a in alerts if "duplicate" in a.alert_type]
        return {"intent": "risk_alerts",
                "answer": f"{len(alerts)} open alert(s).",
                "rows": [{"fdr_uid": a.fdr.fdr_uid if a.fdr else None,
                          "type": a.alert_type, "severity": a.severity.value,
                          "reason": a.reason} for a in alerts]}

    # --- not renewed ---
    if "renew" in q:
        rows = db.query(FDRRecord).filter(
            FDRRecord.maturity_date < today,
            FDRRecord.status != FDRStatus.released,
            ~FDRRecord.id.in_(db.query(RenewalRecord.old_fdr_id).filter(
                RenewalRecord.status == "completed"))
        ).all()
        return {"intent": "not_renewed",
                "answer": f"{len(rows)} expired/maturing FDR(s) have no completed renewal.",
                "rows": [_fdr_line(f) for f in rows]}

    # --- release requests ---
    if "release" in q or "refund" in q:
        rows = db.query(ReleaseRequest).filter(
            ReleaseRequest.status.in_([ReleaseStatus.pending, ReleaseStatus.under_review])).all()
        return {"intent": "release_requests",
                "answer": f"{len(rows)} pending release request(s).",
                "rows": [{"id": r.id, "fdr_uid": r.fdr.fdr_uid if r.fdr else None,
                          "institution": r.fdr.institution.name if r.fdr and r.fdr.institution else None,
                          "status": r.status.value, "reason": r.reason} for r in rows]}

    # --- institution-wise summary ---
    if "institution" in q and ("summary" in q or "wise" in q or "distribution" in q or "per " in q):
        rows = db.query(Institution.name, func.count(FDRRecord.id),
                        func.coalesce(func.sum(FDRRecord.amount), 0)) \
            .join(FDRRecord, FDRRecord.institution_id == Institution.id) \
            .group_by(Institution.name).order_by(func.count(FDRRecord.id).desc()).all()
        return {"intent": "institution_summary",
                "answer": f"FDR distribution across {len(rows)} institution(s).",
                "rows": [{"institution": n, "fdr_count": c, "total_amount": float(a)}
                         for n, c, a in rows]}

    # --- discrepancies for a specific FDR ---
    m = re.search(r"(FDRSETU-\d+|fdr\s*#?\s*(\w[\w\-/]{3,}))", question, re.I)
    if m and ("discrep" in q or "summar" in q or "detail" in q or "status" in q or "show" in q):
        token = m.group(1).upper()
        fdr = db.query(FDRRecord).filter(
            (FDRRecord.fdr_uid == token) | (FDRRecord.fdr_number == token)).first()
        if fdr:
            alerts = db.query(RiskAlert).filter(RiskAlert.fdr_id == fdr.id).all()
            return {"intent": "fdr_detail",
                    "answer": f"FDR {fdr.fdr_uid}: {len(alerts)} alert(s), "
                              f"risk level {fdr.risk_level.value}.",
                    "rows": [_fdr_line(fdr)],
                    "alerts": [{"type": a.alert_type, "severity": a.severity.value,
                                "reason": a.reason} for a in alerts]}
        return {"intent": "fdr_detail", "answer": f"No FDR found matching '{token}'.", "rows": []}

    # --- totals ---
    if "how many" in q or "total" in q or "count" in q:
        total = db.query(func.count(FDRRecord.id)).scalar()
        verified = db.query(func.count(FDRRecord.id)).filter(
            FDRRecord.verification_status == VerificationStatus.verified).scalar()
        insts = db.query(func.count(Institution.id)).scalar()
        return {"intent": "totals",
                "answer": f"{total} FDR(s) registered across {insts} institution(s); "
                          f"{verified} verified.",
                "rows": []}

    return {"intent": "fallback",
            "answer": "I can answer questions about pending verifications, upcoming maturities, "
                      "high-risk records, renewals, release requests, institution-wise summaries, "
                      "and discrepancies in a specific FDR.",
            "rows": []}
