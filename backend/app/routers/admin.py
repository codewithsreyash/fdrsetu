import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import User, Role, Bank, AuditLog, Notification, FDRRecord, Institution
from ..security import hash_password
from ..services.reports import fdrs_to_xlsx, fdrs_to_pdf

router = APIRouter(tags=["admin"])


# ---------- banks ----------
@router.get("/banks")
def list_banks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": b.id, "name": b.name, "short_code": b.short_code,
             "is_demo": b.is_demo} for b in db.query(Bank).order_by(Bank.name).all()]


# ---------- users & roles ----------
class UserIn(BaseModel):
    email: str
    full_name: str
    password: str
    role: str
    institution_id: int | None = None
    bank_id: int | None = None


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name,
            "role": u.role.value, "is_active": u.is_active,
            "institution_id": u.institution_id,
            "institution_name": u.institution.name if u.institution else None,
            "bank_id": u.bank_id, "bank_name": u.bank.name if u.bank else None}


@router.get("/users")
def list_users(db: Session = Depends(get_db),
               user: User = Depends(require_roles(Role.admin))):
    return [user_out(u) for u in db.query(User).order_by(User.id).all()]


@router.post("/users")
def create_user(body: UserIn, db: Session = Depends(get_db),
                user: User = Depends(require_roles(Role.admin))):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(400, "Email already registered")
    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(400, "Invalid role")
    u = User(email=body.email.lower(), full_name=body.full_name,
             password_hash=hash_password(body.password), role=role,
             institution_id=body.institution_id if role == Role.institution else None,
             bank_id=body.bank_id if role == Role.bank else None)
    db.add(u)
    db.flush()
    audit(db, user, "create", "user", u.id, u.email)
    db.commit()
    return user_out(u)


@router.put("/users/{user_id}")
def update_user(user_id: int, body: dict, db: Session = Depends(get_db),
                user: User = Depends(require_roles(Role.admin))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if "is_active" in body:
        u.is_active = bool(body["is_active"])
    if "full_name" in body:
        u.full_name = body["full_name"]
    if "password" in body and body["password"]:
        u.password_hash = hash_password(body["password"])
    if "role" in body:
        u.role = Role(body["role"])
    audit(db, user, "update", "user", u.id, u.email)
    db.commit()
    return user_out(u)


# ---------- notifications ----------
@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Notification).filter(
        (Notification.user_id == user.id) |
        (Notification.role == user.role.value) |
        ((Notification.role == "institution") &
         (Notification.institution_id == user.institution_id))
    ).order_by(Notification.created_at.desc())
    return [{"id": n.id, "title": n.title, "message": n.message, "kind": n.kind,
             "is_read": n.is_read, "created_at": n.created_at.isoformat()}
            for n in q.limit(100).all()]


@router.post("/notifications/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.get(Notification, nid)
    if n:
        n.is_read = True
        db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        (Notification.user_id == user.id) | (Notification.role == user.role.value)
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


# ---------- audit logs ----------
@router.get("/audit-logs")
def audit_logs(limit: int = 200, entity: str | None = None,
               db: Session = Depends(get_db),
               user: User = Depends(require_roles(Role.officer, Role.admin))):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if entity:
        q = q.filter(AuditLog.entity == entity)
    return [{"id": a.id, "user_email": a.user_email, "action": a.action,
             "entity": a.entity, "entity_id": a.entity_id, "detail": a.detail,
             "created_at": a.created_at.isoformat()} for a in q.limit(min(limit, 1000)).all()]


# ---------- report exports ----------
@router.get("/reports/fdrs.xlsx")
def export_xlsx(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(FDRRecord)
    if user.role == Role.institution:
        q = q.filter(FDRRecord.institution_id == user.institution_id)
    data = fdrs_to_xlsx(q.order_by(FDRRecord.created_at.desc()).all())
    return StreamingResponse(io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=fdrsetu-report.xlsx"})


@router.get("/reports/fdrs.pdf")
def export_pdf(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(FDRRecord)
    if user.role == Role.institution:
        q = q.filter(FDRRecord.institution_id == user.institution_id)
    data = fdrs_to_pdf(q.order_by(FDRRecord.created_at.desc()).all())
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fdrsetu-report.pdf"})
