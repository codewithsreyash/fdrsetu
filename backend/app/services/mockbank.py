"""Mock Bank Verification API (SIMULATED — hackathon demo only).

Simulates a bank-side verification service: the bank officer's confirmations
are checked against the seeded MockBankLedger, the 'source of truth' a real
bank API would expose.
"""
from sqlalchemy.orm import Session

from ..models import MockBankLedger


def bank_lookup(db: Session, fdr_number: str) -> dict | None:
    rec = db.query(MockBankLedger).filter(MockBankLedger.fdr_number == fdr_number).first()
    if not rec:
        return None
    return {
        "fdr_number": rec.fdr_number,
        "bank": rec.bank.name if rec.bank else None,
        "branch": rec.branch,
        "ifsc": rec.ifsc,
        "amount": float(rec.amount) if rec.amount else None,
        "issue_date": str(rec.issue_date) if rec.issue_date else None,
        "maturity_date": str(rec.maturity_date) if rec.maturity_date else None,
        "source": "MOCK BANK API — simulated verification",
    }


def verify(db: Session, fdr_number: str, confirmations: dict) -> dict:
    """Compare officer confirmations with the ledger. `confirmations` keys:
    fdr_number_confirmed, amount_confirmed, maturity_confirmed, branch_confirmed."""
    ledger = bank_lookup(db, fdr_number)
    if ledger is None:
        return {"found": False, "result": "not_found",
                "message": f"No record of FDR {fdr_number} at the issuing bank (simulated)."}
    checks = {k: bool(v) for k, v in confirmations.items()}
    all_ok = all(checks.values()) if checks else False
    return {
        "found": True,
        "result": "verified" if all_ok else "mismatch",
        "ledger": ledger,
        "confirmations": checks,
        "message": "All details confirmed by bank (simulated)." if all_ok
                   else "Bank could not confirm one or more details (simulated).",
    }
