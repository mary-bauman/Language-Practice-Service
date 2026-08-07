from datetime import datetime
from typing import Any, Dict, Type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.models import (
    Phrase,
    PracticeEvent,
    SentenceTemplate,
    User,
    Word,
)
from app.db.session import get_session
from app.deps import get_current_user
from app.schemas.practice import PracticeRequest, PracticeResponse
from app.services.scheduler import update_schedule


ITEM_MODELS: Dict[str, Type[Any]] = {
    "word": Word,
    "phrase": Phrase,
    "template": SentenceTemplate,
}

router = APIRouter(tags=["practice"])


@router.post(
    "/practice",
    response_model=PracticeResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_practice(
    payload: PracticeRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    model = ITEM_MODELS[payload.item_type]
    item = session.exec(
        select(model)
        .where(model.id == payload.item_id, model.owner_id == current_user.id)
        .with_for_update()
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    now = datetime.utcnow()
    event = PracticeEvent(
        item_type=payload.item_type,
        item_id=payload.item_id,
        user_id=current_user.id,
        attempted_at=now,
        outcome=payload.outcome,
        details=payload.details,
    )
    update_schedule(item, payload.outcome, now)
    session.add(event)
    session.add(item)
    session.commit()
    session.refresh(event)
    return event
