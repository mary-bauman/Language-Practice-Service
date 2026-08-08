from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import select

from app.db.models import User
from app.db.session import get_session
from app.main import app
from app.schemas.items import (
    ItemCreate,
    ItemUpdate,
    TemplateCreate,
    TemplateUpdate,
)
from app.utils.import_export import _parse_tags, import_items


client = TestClient(app)


def auth():
    username = f"coverage-{uuid4().hex[:12]}"
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password-123"},
    )
    assert response.status_code == 201
    return (
        {"Authorization": f"Bearer {response.json()['access_token']}"},
        username,
    )


def test_phrase_and_template_read_update_paths():
    headers, _ = auth()
    phrase = client.post(
        "/api/v1/phrases",
        headers=headers,
        json={"german": "Guten Morgen", "english": "Good morning"},
    ).json()
    template = client.post(
        "/api/v1/templates",
        headers=headers,
        json={"template_text": "Ich bin {adjective}"},
    ).json()

    phrases = client.get("/api/v1/phrases", headers=headers)
    assert phrases.status_code == 200
    assert phrases.json()["items"][0]["id"] == phrase["id"]
    assert client.get(f"/api/v1/phrases/{phrase['id']}", headers=headers).status_code == 200
    updated_phrase = client.patch(
        f"/api/v1/phrases/{phrase['id']}",
        headers=headers,
        json={"english": "Morning"},
    )
    assert updated_phrase.status_code == 200
    assert updated_phrase.json()["english"] == "Morning"

    assert client.get(f"/api/v1/templates/{template['id']}", headers=headers).status_code == 200


def test_practice_history_and_stats_filters():
    headers, _ = auth()
    word = client.post(
        "/api/v1/words",
        headers=headers,
        json={"german": "laufen", "english": "to run"},
    ).json()
    item_id = word["id"]
    client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": item_id, "outcome": "correct"},
    )
    client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": item_id, "outcome": "incorrect"},
    )
    client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": item_id, "outcome": "correct"},
    )

    history = client.get(
        f"/api/v1/practice?item_type=word&item_id={item_id}"
        "&since=2000-01-01T00:00:00&until=2100-01-01T00:00:00",
        headers=headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 3
    assert client.get(
        "/api/v1/practice?item_type=invalid", headers=headers
    ).status_code == 422

    summary = client.get("/api/v1/stats/summary", headers=headers)
    assert summary.json()["total_attempts"] == 3
    detail = client.get(f"/api/v1/stats/word/{item_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["accuracy"] == 2 / 3
    assert detail.json()["current_correct_streak"] == 1
    assert client.get(
        f"/api/v1/stats/word/{uuid4()}", headers=headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/stats/invalid/{item_id}", headers=headers
    ).status_code == 422


def test_recompute_ignores_history_for_deleted_items():
    headers, _ = auth()
    word = client.post(
        "/api/v1/words",
        headers=headers,
        json={"german": "bleiben", "english": "to stay"},
    ).json()
    client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": word["id"], "outcome": "correct"},
    )
    assert client.delete(f"/api/v1/words/{word['id']}", headers=headers).status_code == 204
    recomputed = client.post("/api/v1/scheduler/recompute", headers=headers)
    assert recomputed.status_code == 200
    assert recomputed.json()["events_replayed"] == 0


def test_schema_and_csv_validation_errors():
    with pytest.raises(ValidationError):
        ItemCreate(german="   ")
    with pytest.raises(ValidationError):
        ItemUpdate(german="   ")
    assert ItemUpdate(german="  neu ").german == "neu"
    with pytest.raises(ValidationError):
        TemplateCreate(template_text="   ")
    with pytest.raises(ValidationError):
        TemplateUpdate(template_text="   ")
    assert TemplateUpdate(template_text="  Ich bin ").template_text == "Ich bin"
    assert _parse_tags("") == {}
    with pytest.raises(ValueError, match="JSON object"):
        _parse_tags("[]")

    headers, username = auth()
    response = client.post(
        "/api/v1/data/import.csv",
        headers=headers,
        files={"file": ("missing.csv", "item_type,german\nword,Haus\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "missing required columns" in response.json()["detail"]

    user = next(get_session())
    try:
        owner = user.exec(select(User).where(User.username == username)).one()
        with pytest.raises(ValueError, match="JSON object"):
            import_items(
                user,
                owner,
                (
                    "item_type,german,english,part_of_speech,source,category,"
                    "template_text,translation_hint,tags\n"
                    "word,Haus,house,,,,,,[]\n"
                ),
            )
    finally:
        user.close()
