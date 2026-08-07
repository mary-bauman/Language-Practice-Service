from datetime import datetime
from typing import Dict, Tuple, Type
from uuid import UUID

from sqlmodel import Session, select

from app.db.models import Phrase, PracticeEvent, SentenceTemplate, User, Word
from app.services.scheduler import update_schedule

ITEM_MODELS: Dict[str, Type] = {
    "word": Word,
    "phrase": Phrase,
    "template": SentenceTemplate,
}


def recompute_user_schedule(session: Session, user: User) -> Dict[str, int]:
    """Rebuild one user's denormalized practice state from practice history."""
    items: Dict[Tuple[str, UUID], object] = {}
    counts = {"items_recomputed": 0, "events_replayed": 0}

    for item_type, model in ITEM_MODELS.items():
        query = select(model).where(model.owner_id == user.id).with_for_update()
        for item in session.exec(query).all():
            item.total_practices = 0
            item.correct_count = 0
            item.last_practiced_at = None
            item.interval_seconds = None
            item.repetitions = 0
            item.ease_factor = 2.5
            item.next_due = None
            item.last_reviewed_at = None
            items[(item_type, item.id)] = item
            counts["items_recomputed"] += 1

    events = session.exec(
        select(PracticeEvent)
        .where(PracticeEvent.user_id == user.id)
        .order_by(PracticeEvent.attempted_at, PracticeEvent.id)
    ).all()
    for event in events:
        item = items.get((event.item_type, event.item_id))
        if item is None:
            # Ignore history for deleted or inaccessible items.
            continue
        update_schedule(item, event.outcome, event.attempted_at)
        counts["events_replayed"] += 1

    session.commit()
    return counts
