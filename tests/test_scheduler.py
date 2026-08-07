from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import Word
from app.db.session import get_session
from app.main import app

client = TestClient(app)


def auth():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": f"recompute-{uuid4().hex[:12]}",
            "password": "password-123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_recompute_repairs_state_and_is_idempotent():
    headers = auth()
    word = client.post(
        "/api/v1/words",
        headers=headers,
        json={"german": "wiederholen", "english": "to repeat"},
    ).json()
    word_id = word["id"]

    for outcome in ("correct", "correct", "incorrect"):
        response = client.post(
            "/api/v1/practice",
            headers=headers,
            json={"item_type": "word", "item_id": word_id, "outcome": outcome},
        )
        assert response.status_code == 201

    session = next(get_session())
    try:
        stored = session.get(Word, word_id)
        stored.total_practices = 999
        stored.correct_count = 999
        stored.repetitions = 999
        stored.interval_seconds = 999
        session.add(stored)
        session.commit()
    finally:
        session.close()

    recomputed = client.post("/api/v1/scheduler/recompute", headers=headers)
    assert recomputed.status_code == 200
    assert recomputed.json() == {"items_recomputed": 1, "events_replayed": 3}

    repaired = client.get(f"/api/v1/words/{word_id}", headers=headers).json()
    assert repaired["total_practices"] == 3
    assert repaired["correct_count"] == 2
    assert repaired["repetitions"] == 0
    assert repaired["interval_seconds"] == 60

    repeated = client.post("/api/v1/scheduler/recompute", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json() == {"items_recomputed": 1, "events_replayed": 3}
    assert client.get(f"/api/v1/words/{word_id}", headers=headers).json() == repaired


def test_recompute_requires_auth_and_is_user_scoped():
    assert client.post("/api/v1/scheduler/recompute").status_code == 401
    owner_headers = auth()
    other_headers = auth()
    word = client.post(
        "/api/v1/words",
        headers=owner_headers,
        json={"german": "sicher", "english": "sure"},
    ).json()
    client.post(
        "/api/v1/practice",
        headers=owner_headers,
        json={"item_type": "word", "item_id": word["id"], "outcome": "correct"},
    )
    response = client.post(
        "/api/v1/scheduler/recompute",
        headers=other_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"items_recomputed": 0, "events_replayed": 0}
