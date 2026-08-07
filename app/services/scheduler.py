from datetime import datetime, timedelta
from typing import Any


INITIAL_INTERVAL_SECONDS = 60
MAX_EASE_FACTOR = 3.0
MIN_EASE_FACTOR = 1.3


def update_schedule(item: Any, outcome: str, now: datetime) -> None:
    """Apply a small SM-2-style update to an item after one attempt."""
    item.last_reviewed_at = now
    item.last_practiced_at = now
    item.total_practices += 1

    if outcome == "correct":
        item.correct_count += 1
        item.repetitions += 1
        previous_interval = item.interval_seconds or INITIAL_INTERVAL_SECONDS
        item.interval_seconds = max(
            INITIAL_INTERVAL_SECONDS,
            round(previous_interval * item.ease_factor),
        )
        item.ease_factor = min(MAX_EASE_FACTOR, item.ease_factor + 0.1)
    elif outcome == "incorrect":
        item.repetitions = 0
        item.interval_seconds = INITIAL_INTERVAL_SECONDS
        item.ease_factor = max(MIN_EASE_FACTOR, item.ease_factor - 0.2)
    else:
        item.interval_seconds = item.interval_seconds or INITIAL_INTERVAL_SECONDS

    item.next_due = now + timedelta(seconds=item.interval_seconds)
