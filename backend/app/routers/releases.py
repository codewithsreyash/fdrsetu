import io
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import (
    ReleaseRequest, ReleaseStatus, ApprovalHistory, FDRRecord, FDRStatus,
    User, Role, Notification,
)

router = APIRouter(prefix="/releases", tags=["releases"])


def release_out(r: ReleaseRequest) -> dict:
    return {
        "id": r.id, "fdr_id": r.fdr_id,
        "fdr_uid": r.fdr.fdr_uid if r.fdr else None,
        "fdr_number": r.fdr.fdr_number if r.fdr else None,
        "amount": float(r.fdr.amount) if r.fdr and r.fdr.amount else None,
        "institution": r.fdr.institution.name if r.fdr and r.fdr.institution else None,
        "bank": r.fdr.bank.name if r.fdr and r.fdr.bank else None,
        "maturity_date": str(r.fdr.maturity_date) if r.fdr else None,
        "reason": r.reason, "status": r.status.value,
        "has_document": bool(r.supporting_doc_path or r.supporting_doc_bytes),
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("")
def list_releases(status: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(ReleaseRequest).order_by(ReleaseRequest.created_at.desc())
    if user.role == Role.institution:
        q = q.filter(ReleaseRequest.institution_id == user.institution_id)
    if status:
        q = q.filter(ReleaseRequest.status == status)
    return [release_out(r) for r in q.all()]


@router.post("")
def create_release(fdr_id: int = Form(...), reason: str = Form(""),
                   file: UploadFile | None = File(None),
                   db: Session = Depends(get_db),
                   user: User = Depends(require_roles(Role.institution))):
    fdr = db.get(FDRRecord, fdr_id)
    if not fdr:
        raise HTTPException(404, "FDR not found")
    if fdr.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    if fdr.status == FDRStatus.released:
        raise HTTPException(400, "FDR already released")
    existing = db.query(ReleaseRequest).filter(
        ReleaseRequest.fdr_id == fdr_id,
        ReleaseRequest.status.in_([ReleaseStatus.pending, ReleaseStatus.under_review])).first()
    if existing:
        raise HTTPException(400, "A release request is already pending for this FDR")

    path = None
    doc_bytes = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".pdf", ".jpg", ".jpeg", ".png"):
            raise HTTPException(400, "Supporting document must be PDF/JPG/PNG")
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        path = os.path.join(settings.UPLOAD_DIR, f"rel-{uuid.uuid4().hex}{ext}")
        doc_bytes = file.file.read()
        with open(path, "wb") as fh:
            fh.write(doc_bytes)

    r = ReleaseRequest(fdr_id=fdr_id, institution_id=user.institution_id,
                       reason=reason, supporting_doc_path=path,
                       supporting_doc_bytes=doc_bytes,
                       supporting_doc_name=file.filename if file else None,
                       supporting_doc_type=file.content_type if file else None)
    db.add(r)
    db.add(Notification(
        role="officer", title="New release request",
        message=f"Release request for {fdr.fdr_uid} ({fdr.fdr_number}) from "
                f"{fdr.institution.name if fdr.institution else ''}.",
        kind="release"))
    audit(db, user, "create_release_request", "fdr", fdr.id, fdr.fdr_uid)
    db.commit()
    return release_out(r)


class OfficerAction(BaseModel):
    action: str          # under_review / approved / rejected / observation
    remarks: str | None = None


@router.post("/{release_id}/action")
def officer_action(release_id: int, body: OfficerAction, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(Role.officer, Role.admin))):
    r = db.get(ReleaseRequest, release_id)
    if not r:
        raise HTTPException(404, "Release request not found")
    mapping = {"under_review": ReleaseStatus.under_review,
               "approved": ReleaseStatus.approved,
               "rejected": ReleaseStatus.rejected}
    if body.action == "observation":
        db.add(ApprovalHistory(release_request_id=r.id, officer_id=user.id,
                               action="observation", remarks=body.remarks))
        audit(db, user, "release_observation", "release_request", r.id, body.remarks)
    elif body.action in mapping:
        if r.status in (ReleaseStatus.approved, ReleaseStatus.rejected):
            raise HTTPException(400, f"Request already {r.status.value}")
        r.status = mapping[body.action]
        db.add(ApprovalHistory(release_request_id=r.id, officer_id=user.id,
                               action=body.action, remarks=body.remarks))
        if body.action == "approved":
            r.fdr.status = FDRStatus.released
        db.add(Notification(
            role="institution", institution_id=r.institution_id,
            title=f"Release request {body.action}",
            message=f"Release request #{r.id} for {r.fdr.fdr_uid} was {body.action} "
                    f"by an AICTE officer. {body.remarks or ''}",
            kind="release"))
        audit(db, user, f"release_{body.action}", "release_request", r.id, body.remarks)
    else:
        raise HTTPException(400, "action must be under_review|approved|rejected|observation")
    db.commit()
    return release_out(r)


@router.get("/{release_id}/document")
def release_document(release_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    r = db.get(ReleaseRequest, release_id)
    if not r:
        raise HTTPException(404, "Release request not found")
    if user.role == Role.institution and r.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    data = None
    if r.supporting_doc_path and os.path.exists(r.supporting_doc_path):
        with open(r.supporting_doc_path, "rb") as fh:
            data = fh.read()
    elif r.supporting_doc_bytes:
        data = r.supporting_doc_bytes
    if data is None:
        raise HTTPException(404, "No supporting document")
    return StreamingResponse(
        io.BytesIO(data), media_type=r.supporting_doc_type or "application/octet-stream",
        headers={"Content-Disposition":
                 f'inline; filename="{r.supporting_doc_name or "document"}"'})


@router.get("/{release_id}/history")
def release_history(release_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    r = db.get(ReleaseRequest, release_id)
    if not r:
        raise HTTPException(404, "Release request not found")
    if user.role == Role.institution and r.institution_id != user.institution_id:
        raise HTTPException(403, "Access denied")
    rows = db.query(ApprovalHistory).filter(
        ApprovalHistory.release_request_id == release_id) \
        .order_by(ApprovalHistory.created_at).all()
    return [{"id": h.id, "action": h.action, "remarks": h.remarks,
             "officer": db.get(User, h.officer_id).email if h.officer_id else None,
             "created_at": h.created_at.isoformat()} for h in rows]
