from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, audit
from ..models import User
from ..services.copilot import answer_question

router = APIRouter(prefix="/copilot", tags=["copilot"])


class AskIn(BaseModel):
    question: str


SUGGESTED = [
    "How many FDRs are pending verification?",
    "Which institutions have FDRs expiring in the next 30 days?",
    "Show high-risk FDR records",
    "Which FDRs have not been renewed?",
    "Show pending release requests",
    "Generate an institution-wise FDR summary",
]


@router.post("/ask")
def ask(body: AskIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = answer_question(db, body.question)
    audit(db, user, "copilot_ask", None, None, body.question[:200])
    db.commit()
    return result


@router.get("/suggested")
def suggested(user: User = Depends(get_current_user)):
    return SUGGESTED
