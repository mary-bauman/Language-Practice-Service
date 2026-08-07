from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def auth():
    response = client.post(
        "/api/v1/auth/register",
        json={"username": f"practice-{uuid4().hex[:12]}", "password": "password-123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_word(headers):
    response = client.post(
        "/api/v1/words",
        headers=headers,
        json={"german": "lernen", "english": "to learn"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_practice_updates_counters_and_schedule():
    headers = auth()
    item_id = create_word(headers)

    first = client.post(
        "/api/v1/practice",
        headers=headers,
        json={
            "item_type": "word",
            "item_id": item_id,
            "outcome": "correct",
            "details": {"response_ms": 420},
        },
    )
    assert first.status_code == 201
    assert first.json()["outcome"] == "correct"

    item = client.get(f"/api/v1/words/{item_id}", headers=headers).json()
    assert item["total_practices"] == 1
    assert item["correct_count"] == 1
    assert item["repetitions"] == 1
    assert item["interval_seconds"] == 150
    assert item["next_due"] is not None

    second = client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": item_id, "outcome": "incorrect"},
    )
    assert second.status_code == 201
    item = client.get(f"/api/v1/words/{item_id}", headers=headers).json()
    assert item["total_practices"] == 2
    assert item["correct_count"] == 1
    assert item["repetitions"] == 0
    assert item["interval_seconds"] == 60


def test_practice_supports_phrase_and_template():
    headers = auth()
    phrase = client.post(
        "/api/v1/phrases",
        headers=headers,
        json={"german": "Ich möchte", "english": "I would like"},
    ).json()
    template = client.post(
        "/api/v1/templates",
        headers=headers,
        json={"template_text": "Ich möchte {noun}"},
    ).json()

    for item_type, item_id in [("phrase", phrase["id"]), ("template", template["id"])]:
        response = client.post(
            "/api/v1/practice",
            headers=headers,
            json={"item_type": item_type, "item_id": item_id, "outcome": "skipped"},
        )
        assert response.status_code == 201


def test_practice_rejects_invalid_or_unowned_items():
    headers = auth()
    other_headers = auth()
    item_id = create_word(headers)

    invalid_type = client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "sentence", "item_id": item_id, "outcome": "correct"},
    )
    assert invalid_type.status_code == 422

    invalid_outcome = client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": item_id, "outcome": "maybe"},
    )
    assert invalid_outcome.status_code == 422

    unowned = client.post(
        "/api/v1/practice",
        headers=other_headers,
        json={"item_type": "word", "item_id": item_id, "outcome": "correct"},
    )
    assert unowned.status_code == 404

    missing = client.post(
        "/api/v1/practice",
        headers=headers,
        json={"item_type": "word", "item_id": str(uuid4()), "outcome": "correct"},
    )
    assert missing.status_code == 404


def test_concurrent_practice_requests_preserve_both_updates():
    headers = auth()
    item_id = create_word(headers)

    def practice_once():
        return client.post(
            "/api/v1/practice",
            headers=headers,
            json={"item_type": "word", "item_id": item_id, "outcome": "correct"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: practice_once(), range(2)))

    assert [response.status_code for response in responses] == [201, 201]
    item = client.get(f"/api/v1/words/{item_id}", headers=headers).json()
    assert item["total_practices"] == 2
    assert item["correct_count"] == 2
