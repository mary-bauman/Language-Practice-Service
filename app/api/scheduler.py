from typing import Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.models import User
from app.db.session import get_session
from app.deps import get_current_user
from app.services.recompute import recompute_user_schedule

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/recompute")
def recompute_schedule(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Dict[str, int]:
    return recompute_user_schedule(session, current_user)
