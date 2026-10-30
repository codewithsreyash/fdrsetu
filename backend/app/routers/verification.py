from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import (
    FDRRecord, FDRStatus, VerificationRequest, VerificationHistory,
    VerificationStatus, User, Role, Notification,
)
from ..services import mockbank

router = APIRouter(prefix="/verification", tags=["verification"])


class RequestIn(BaseModel):
    fdr_id: int


class BankVerifyIn(BaseModel):
    fdr_id: int
    confirm_fdr_number: bool
    confirm_amount: bool
    confirm_maturity_date: bool
    confirm_branch: bool
    remarks: str | None = None
    mark_verified: bool          # bank officer's overall verdict


@router.get("/requests")
def list_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(VerificationRequest).order_by(VerificationRequest.created_at.desc())
    if user.role == Role.bank:
        q = q.join(FDRRecord, VerificationRequest.fdr_id == FDRRecord.id) \
             .filter(FDRRecord.bank_id == user.bank_id)
    elif user.role == Role.institution:
        q = q.join(FDRRecord, VerificationRequest.fdr_id == FDRRecord.id) \
             .filter(FDRRecord.institution_id == user.institution_id)
    out = []
    for r in q.all():
        out.append({"id": r.id, "fdr_id": r.fdr_id, "status": r.status.value,
                    "created_at": r.created_at.isoformat(),
                    "fdr_uid": r.fdr.fdr_uid, "fdr_number": r.fdr.fdr_number,
                    "institution": r.fdr.institution.name if r.fdr.institution else None,
                    "bank": r.fdr.bank.name if r.fdr.bank else None,
                    "amount": float(r.fdr.amount), "branch": r.fdr.branch,
                    "ifsc": r.fdr.ifsc, "maturity_date": str(r.fdr.maturity_date)})
    return out


@router.post("/requests")
def create_request(body: RequestIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    fdr = db.get(FDRRecord, body.fdr_id)
    if not fdr:
        raise HTTPException(404, "FDR not found")
    if user.role == Role.institution and fdr.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    if user.role == Role.bank:
        raise HTTPException(403, "Bank officers cannot request verification")
    existing = db.query(VerificationRequest).filter(
        VerificationRequest.fdr_id == fdr.id,
        VerificationRequest.status.in_([VerificationStatus.pending, VerificationStatus.in_review])
    ).first()
    if existing:
        return {"id": existing.id, "status": existing.status.value, "detail": "Already requested"}
    r = VerificationRequest(fdr_id=fdr.id, requested_by_id=user.id)
    fdr.verification_status = VerificationStatus.in_review
    db.add(r)
    audit(db, user, "request_verification", "fdr", fdr.id, fdr.fdr_uid)
    db.commit()
    return {"id": r.id, "status": r.status.value}


@router.get("/bank-lookup/{fdr_number}")
def bank_lookup(fdr_number: str, db: Session = Depends(get_db),
                user: User = Depends(require_roles(Role.bank, Role.officer, Role.admin))):
    """Simulated bank-side record lookup (mock bank API)."""
    rec = mockbank.bank_lookup(db, fdr_number)
    if not rec:
        return {"found": False, "source": "MOCK BANK API — simulated verification"}
    return {"found": True, "ledger": rec}


@router.post("/bank-verify")
def bank_verify(body: BankVerifyIn, db: Session = Depends(get_db),
                user: User = Depends(require_roles(Role.bank))):
    """Bank officer submits verification — checked against the mock bank ledger."""
    fdr = db.get(FDRRecord, body.fdr_id)
    if not fdr:
        raise HTTPException(404, "FDR not found")
    if fdr.bank_id != user.bank_id:
        raise HTTPException(403, "This FDR belongs to a different bank")

    confirmations = {
        "fdr_number": body.confirm_fdr_number,
        "amount": body.confirm_amount,
        "maturity_date": body.confirm_maturity_date,
        "branch": body.confirm_branch,
    }
    api_result = mockbank.verify(db, fdr.fdr_number, confirmations)
    if body.mark_verified and api_result.get("result") == "verified":
        result = "verified"
    elif not api_result.get("found"):
        result = "not_found"
    else:
        result = "mismatch" if body.mark_verified else "rejected"

    vh = VerificationHistory(
        fdr_id=fdr.id, officer_id=user.id,
        bank_confirmed_number=body.confirm_fdr_number,
        bank_confirmed_amount=body.confirm_amount,
        bank_confirmed_maturity=body.confirm_maturity_date,
        bank_confirmed_branch=body.confirm_branch,
        result=result, remarks=body.remarks, mock_api=True,
    )
    req = db.query(VerificationRequest).filter(
        VerificationRequest.fdr_id == fdr.id,
        VerificationRequest.status.in_([VerificationStatus.pending, VerificationStatus.in_review])
    ).first()
    if req:
        req.status = VerificationStatus.verified if result == "verified" else VerificationStatus.rejected
        vh.verification_request_id = req.id

    fdr.verification_status = VerificationStatus.verified if result == "verified" else VerificationStatus.rejected
    if result == "verified":
        fdr.status = FDRStatus.verified
    db.add(vh)
    db.add(Notification(
        role="officer", title=f"Bank verification {result}",
        message=f"Bank verified FDR {fdr.fdr_uid} ({fdr.fdr_number}) — result: {result} (simulated).",
        kind="verification"))
    db.add(Notification(
        role="institution", institution_id=fdr.institution_id,
        title=f"Bank verification {result}",
        message=f"Your FDR {fdr.fdr_uid} was {result} by {fdr.bank.name if fdr.bank else 'bank'} (simulated).",
        kind="verification"))
    audit(db, user, "bank_verify", "fdr", fdr.id, f"{fdr.fdr_uid}: {result}")
    db.commit()
    return {"result": result, "mock_api_result": api_result}


@router.get("/history")
def verification_history(fdr_id: int | None = None, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    q = db.query(VerificationHistory).order_by(VerificationHistory.created_at.desc())
    if fdr_id:
        q = q.filter(VerificationHistory.fdr_id == fdr_id)
    if user.role == Role.institution:
        q = q.join(FDRRecord, VerificationHistory.fdr_id == FDRRecord.id) \
             .filter(FDRRecord.institution_id == user.institution_id)
    return [{"id": v.id, "fdr_id": v.fdr_id,
             "fdr_uid": v.fdr.fdr_uid if v.fdr else None,
             "result": v.result, "remarks": v.remarks, "mock_api": v.mock_api,
             "confirmed": {"number": v.bank_confirmed_number, "amount": v.bank_confirmed_amount,
                           "maturity": v.bank_confirmed_maturity, "branch": v.bank_confirmed_branch},
             "created_at": v.created_at.isoformat()} for v in q.limit(200).all()]
