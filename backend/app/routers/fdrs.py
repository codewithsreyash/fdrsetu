import io
import json
import os
import uuid
from datetime import date, datetime

import qrcode
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..config import settings
from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import (
    FDRRecord, FDRStatus, RiskLevel, VerificationStatus, Institution, Bank,
    FDRDocument, User, Role, RenewalRecord,
)
from ..services.ocr import extract_document
from ..services.risk import run_risk_checks

router = APIRouter(prefix="/fdrs", tags=["fdrs"])

ALLOWED_UPLOAD = {".pdf", ".jpg", ".jpeg", ".png"}


def fdr_out(f: FDRRecord) -> dict:
    return {
        "id": f.id, "fdr_uid": f.fdr_uid, "fdr_number": f.fdr_number,
        "institution_id": f.institution_id,
        "institution_name": f.institution.name if f.institution else None,
        "bank_id": f.bank_id, "bank_name": f.bank.name if f.bank else None,
        "branch": f.branch, "ifsc": f.ifsc,
        "amount": float(f.amount) if f.amount else None,
        "interest_rate": float(f.interest_rate) if f.interest_rate else None,
        "issue_date": str(f.issue_date), "maturity_date": str(f.maturity_date),
        "status": f.status.value, "verification_status": f.verification_status.value,
        "risk_level": f.risk_level.value,
        "renewed_from_id": f.renewed_from_id,
        "is_demo": f.is_demo,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "documents": [{"id": d.id, "filename": d.filename,
                       "extraction_status": d.extraction_status} for d in f.documents],
        "open_alerts": len([a for a in f.risk_alerts if a.status == "open"]),
    }


def _visible_query(user: User, db: Session):
    q = db.query(FDRRecord)
    if user.role == Role.institution:
        q = q.filter(FDRRecord.institution_id == user.institution_id)
    elif user.role == Role.bank:
        q = q.filter(FDRRecord.bank_id == user.bank_id)
    return q


@router.get("")
def list_fdrs(search: str | None = None, status: str | None = None,
              verification_status: str | None = None, risk_level: str | None = None,
              bank_id: int | None = None, institution_id: int | None = None,
              expiring_days: int | None = None, expired: bool | None = None,
              sort_by: str = "created_at", sort_dir: str = "desc",
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _visible_query(user, db)
    if search:
        like = f"%{search}%"
        q = q.join(Institution, FDRRecord.institution_id == Institution.id) \
             .join(Bank, FDRRecord.bank_id == Bank.id) \
             .filter(or_(FDRRecord.fdr_number.ilike(like), FDRRecord.fdr_uid.ilike(like),
                         FDRRecord.ifsc.ilike(like), FDRRecord.branch.ilike(like),
                         Institution.name.ilike(like), Bank.name.ilike(like)))
    if status:
        q = q.filter(FDRRecord.status == status)
    if verification_status:
        q = q.filter(FDRRecord.verification_status == verification_status)
    if risk_level:
        q = q.filter(FDRRecord.risk_level == risk_level)
    if bank_id:
        q = q.filter(FDRRecord.bank_id == bank_id)
    if institution_id:
        q = q.filter(FDRRecord.institution_id == institution_id)
    if expiring_days:
        from datetime import timedelta
        q = q.filter(FDRRecord.maturity_date >= date.today(),
                     FDRRecord.maturity_date <= date.today() + timedelta(days=expiring_days))
    if expired:
        q = q.filter(FDRRecord.maturity_date < date.today())

    col = getattr(FDRRecord, sort_by, FDRRecord.created_at)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())
    return [fdr_out(f) for f in q.all()]


@router.get("/{fdr_id}")
def get_fdr(fdr_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.get(FDRRecord, fdr_id)
    if not f:
        raise HTTPException(404, "FDR not found")
    if user.role == Role.institution and f.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    if user.role == Role.bank and f.bank_id != user.bank_id:
        raise HTTPException(403, "Access denied")
    out = fdr_out(f)
    out["risk_alerts"] = [{"id": a.id, "type": a.alert_type, "severity": a.severity.value,
                           "reason": a.reason, "status": a.status,
                           "created_at": a.created_at.isoformat()} for a in f.risk_alerts]
    return out


class FDRIn(BaseModel):
    fdr_number: str
    bank_id: int
    institution_id: int | None = None
    branch: str | None = None
    ifsc: str | None = None
    amount: float
    interest_rate: float | None = None
    issue_date: date
    maturity_date: date
    document_id: int | None = None
    renewed_from_id: int | None = None


@router.post("")
def create_fdr(body: FDRIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    if user.role == Role.institution:
        inst_id = user.institution_id
    elif user.role in (Role.officer, Role.admin):
        inst_id = body.institution_id
    else:
        raise HTTPException(403, "Bank officers cannot register FDRs")
    if not inst_id or not db.get(Institution, inst_id):
        raise HTTPException(400, "Valid institution_id required")
    if not db.get(Bank, body.bank_id):
        raise HTTPException(400, "Valid bank_id required")

    seq = db.query(func.count(FDRRecord.id)).scalar() + 1
    fdr = FDRRecord(
        fdr_uid=f"FDRSETU-{seq:05d}", fdr_number=body.fdr_number.strip(),
        institution_id=inst_id, bank_id=body.bank_id, branch=body.branch,
        ifsc=(body.ifsc or "").upper() or None, amount=body.amount,
        interest_rate=body.interest_rate, issue_date=body.issue_date,
        maturity_date=body.maturity_date,
        status=FDRStatus.active if body.issue_date <= date.today() else FDRStatus.pending,
        renewed_from_id=body.renewed_from_id, created_by_id=user.id, is_demo=True,
    )
    db.add(fdr)
    db.flush()

    if body.document_id:
        doc = db.get(FDRDocument, body.document_id)
        if doc:
            doc.fdr_id = fdr.id
    if body.renewed_from_id:
        old = db.get(FDRRecord, body.renewed_from_id)
        if old:
            old.status = FDRStatus.renewed
            rr = db.query(RenewalRecord).filter(
                RenewalRecord.old_fdr_id == old.id,
                RenewalRecord.status != "completed").first()
            if rr:
                rr.new_fdr_id = fdr.id
                rr.status = "completed"
            else:
                db.add(RenewalRecord(old_fdr_id=old.id, new_fdr_id=fdr.id,
                                     institution_id=inst_id, status="completed"))

    run_risk_checks(db, fdr)
    audit(db, user, "create", "fdr", fdr.id, f"{fdr.fdr_uid} / {fdr.fdr_number}")
    db.commit()
    return fdr_out(fdr)


@router.put("/{fdr_id}")
def update_fdr(fdr_id: int, body: FDRIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    f = db.get(FDRRecord, fdr_id)
    if not f:
        raise HTTPException(404, "FDR not found")
    if user.role == Role.institution and f.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    if user.role == Role.bank:
        raise HTTPException(403, "Bank officers cannot edit FDRs")
    for k, v in body.model_dump(exclude={"institution_id", "document_id"}).items():
        setattr(f, k, v)
    run_risk_checks(db, f)
    audit(db, user, "update", "fdr", f.id, f.fdr_uid)
    db.commit()
    return fdr_out(f)


# ---------- document upload + AI extraction ----------

@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...),
                          fdr_id: int | None = Form(None),
                          db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_UPLOAD:
        raise HTTPException(400, f"Unsupported file type {ext}. Use PDF, JPG or PNG.")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, stored)
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 20 MB)")
    with open(path, "wb") as fh:
        fh.write(content)

    extraction = extract_document(path)
    doc = FDRDocument(
        fdr_id=fdr_id, uploaded_by_id=user.id, filename=file.filename,
        stored_path=path, content=content, content_type=file.content_type,
        extracted_data=json.dumps(extraction),
        extraction_status="mock" if extraction["mock"] else "done",
    )
    db.add(doc)
    audit(db, user, "upload_document", "fdr_document", doc.id, file.filename)
    db.commit()
    return {"document_id": doc.id, "filename": doc.filename,
            "extraction_status": doc.extraction_status, "extraction": extraction}


@router.get("/documents/{doc_id}/extraction")
def get_extraction(doc_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    doc = db.get(FDRDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"document_id": doc.id, "filename": doc.filename,
            "extraction_status": doc.extraction_status,
            "extraction": json.loads(doc.extracted_data or "{}")}


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    doc = db.get(FDRDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if os.path.exists(doc.stored_path):
        with open(doc.stored_path, "rb") as fh:
            data = fh.read()
    elif doc.content:
        data = doc.content
    else:
        raise HTTPException(404, "Document file not found")
    return StreamingResponse(io.BytesIO(data), media_type=doc.content_type or "application/octet-stream",
                             headers={"Content-Disposition": f'inline; filename="{doc.filename}"'})


@router.get("/{fdr_id}/qrcode")
def fdr_qr(fdr_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.get(FDRRecord, fdr_id)
    if not f:
        raise HTTPException(404, "FDR not found")
    payload = f"FDRSETU|{f.fdr_uid}|{f.fdr_number}|{f.institution.name if f.institution else ''}"
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="image/png")


@router.get("/{fdr_id}/history")
def fdr_history(fdr_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Complete lifecycle history of an FDR."""
    from ..models import VerificationHistory, ReleaseRequest, ApprovalHistory, RenewalRecord, AuditLog
    f = db.get(FDRRecord, fdr_id)
    if not f:
        raise HTTPException(404, "FDR not found")
    verifs = db.query(VerificationHistory).filter(VerificationHistory.fdr_id == fdr_id).all()
    renewals_new = db.query(RenewalRecord).filter(RenewalRecord.new_fdr_id == fdr_id).all()
    renewals_old = db.query(RenewalRecord).filter(RenewalRecord.old_fdr_id == fdr_id).all()
    releases = db.query(ReleaseRequest).filter(ReleaseRequest.fdr_id == fdr_id).all()
    approvals = []
    for r in releases:
        approvals += db.query(ApprovalHistory).filter(
            ApprovalHistory.release_request_id == r.id).all()
    audits = db.query(AuditLog).filter(AuditLog.entity == "fdr", AuditLog.entity_id == fdr_id).all()

    events = []
    for v in verifs:
        events.append({"at": v.created_at.isoformat(), "type": "verification",
                       "detail": f"Verification {v.result} — {v.remarks or ''}"})
    for r in renewals_new:
        events.append({"at": r.created_at.isoformat(), "type": "renewal",
                       "detail": f"Renewed from FDR #{r.old_fdr_id} (status {r.status})"})
    for r in renewals_old:
        events.append({"at": r.created_at.isoformat(), "type": "renewal",
                       "detail": f"Renewal requested → new FDR #{r.new_fdr_id} ({r.status})"})
    for r in releases:
        events.append({"at": r.created_at.isoformat(), "type": "release",
                       "detail": f"Release request #{r.id} — {r.status.value}"})
    for a in approvals:
        events.append({"at": a.created_at.isoformat(), "type": "approval",
                       "detail": f"Officer action: {a.action} — {a.remarks or ''}"})
    for a in audits:
        events.append({"at": a.created_at.isoformat(), "type": "audit",
                       "detail": f"{a.user_email or 'system'}: {a.action} — {a.detail or ''}"})
    events.append({"at": f.created_at.isoformat(), "type": "created",
                   "detail": f"FDR {f.fdr_uid} registered"})
    events.sort(key=lambda e: e["at"])
    return {"fdr_uid": f.fdr_uid, "events": events}
