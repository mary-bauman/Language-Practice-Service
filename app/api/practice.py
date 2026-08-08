from datetime import datetime
from typing import Any, Dict, Type

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


@router.get("/practice", response_model=list[PracticeResponse])
def list_practice(
    item_type: Optional[str] = Query(default=None),
    item_id: Optional[UUID] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if item_type is not None and item_type not in ITEM_MODELS:
        raise HTTPException(status_code=422, detail="Invalid item_type")
    query = select(PracticeEvent).where(PracticeEvent.user_id == current_user.id)
    if item_type is not None:
        query = query.where(PracticeEvent.item_type == item_type)
    if item_id is not None:
        query = query.where(PracticeEvent.item_id == item_id)
    if since is not None:
        query = query.where(PracticeEvent.attempted_at >= since)
    if until is not None:
        query = query.where(PracticeEvent.attempted_at <= until)
    return session.exec(query.order_by(PracticeEvent.attempted_at)).all()


def _owned_events(
    session: Session, user_id: UUID, item_type: str, item_id: UUID
) -> list[PracticeEvent]:
    if item_type not in ITEM_MODELS:
        raise HTTPException(status_code=422, detail="Invalid item_type")
    model = ITEM_MODELS[item_type]
    item = session.exec(
        select(model).where(model.id == item_id, model.owner_id == user_id)
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return session.exec(
        select(PracticeEvent)
        .where(
            PracticeEvent.user_id == user_id,
            PracticeEvent.item_type == item_type,
            PracticeEvent.item_id == item_id,
        )
        .order_by(PracticeEvent.attempted_at)
    ).all()


@router.get("/stats/summary")
def stats_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    events = session.exec(
        select(PracticeEvent).where(PracticeEvent.user_id == current_user.id)
    ).all()
    return {
        "items_practiced": len({(event.item_type, event.item_id) for event in events}),
        "total_attempts": len(events),
        "correct_attempts": sum(event.outcome == "correct" for event in events),
        "accuracy": (
            sum(event.outcome == "correct" for event in events) / len(events)
            if events
            else 0.0
        ),
    }


@router.get("/stats/{item_type}/{item_id}")
def item_stats(
    item_type: str,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    events = _owned_events(session, current_user.id, item_type, item_id)
    correct = sum(event.outcome == "correct" for event in events)
    streak = 0
    for event in reversed(events):
        if event.outcome != "correct":
            break
        streak += 1
    return {
        "item_type": item_type,
        "item_id": str(item_id),
        "total_attempts": len(events),
        "correct_attempts": correct,
        "accuracy": correct / len(events) if events else 0.0,
        "current_correct_streak": streak,
        "events": events,
    }
