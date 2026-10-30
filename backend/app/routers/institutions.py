from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..deps import require_roles, get_current_user, audit
from ..models import Institution, Role, User, FDRRecord
from ..security import hash_password

router = APIRouter(prefix="/institutions", tags=["institutions"])


class InstitutionIn(BaseModel):
    name: str
    code: str | None = None
    institution_type: str = "Engineering College"
    state: str | None = None
    city: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


def inst_out(i: Institution, db: Session) -> dict:
    return {
        "id": i.id, "code": i.code, "name": i.name,
        "institution_type": i.institution_type, "state": i.state, "city": i.city,
        "contact_email": i.contact_email, "contact_phone": i.contact_phone,
        "is_demo": i.is_demo,
        "fdr_count": db.query(func.count(FDRRecord.id))
                       .filter(FDRRecord.institution_id == i.id).scalar(),
        "total_amount": float(db.query(func.coalesce(func.sum(FDRRecord.amount), 0))
                              .filter(FDRRecord.institution_id == i.id).scalar()),
    }


@router.get("")
def list_institutions(search: str | None = None, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    q = db.query(Institution)
    if user.role == Role.institution:
        q = q.filter(Institution.id == user.institution_id)
    if search:
        q = q.filter(Institution.name.ilike(f"%{search}%") | Institution.code.ilike(f"%{search}%"))
    return [inst_out(i, db) for i in q.order_by(Institution.name).all()]


@router.post("")
def create_institution(body: InstitutionIn, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Role.officer, Role.admin))):
    if db.query(Institution).filter(Institution.code == body.code).first():
        raise HTTPException(400, "Institution code already exists")
    i = Institution(**body.model_dump())
    if not i.code:
        i.code = f"INST-{i.id or db.query(func.count(Institution.id)).scalar() + 1:03d}"
    db.add(i)
    db.flush()
    audit(db, user, "create", "institution", i.id, i.name)
    db.commit()
    return inst_out(i, db)


@router.get("/{inst_id}")
def get_institution(inst_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    i = db.get(Institution, inst_id)
    if not i:
        raise HTTPException(404, "Institution not found")
    if user.role == Role.institution and user.institution_id != inst_id:
        raise HTTPException(403, "Access denied")
    return inst_out(i, db)


@router.put("/{inst_id}")
def update_institution(inst_id: int, body: InstitutionIn, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Role.officer, Role.admin))):
    i = db.get(Institution, inst_id)
    if not i:
        raise HTTPException(404, "Institution not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(i, k, v)
    audit(db, user, "update", "institution", i.id, i.name)
    db.commit()
    return inst_out(i, db)
