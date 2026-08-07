from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def auth():
    response = client.post(
        "/api/v1/auth/register",
        json={"username": f"crud-{uuid4().hex[:12]}", "password": "password-123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_words_crud_and_pagination():
    headers = auth()
    created = client.post(
        "/api/v1/words",
        headers=headers,
        json={"german": "  Haus ", "english": "house", "tags": {"topic": "home"}},
    )
    assert created.status_code == 201
    word = created.json()
    assert word["german"] == "Haus"

    listed = client.get("/api/v1/words?limit=1&offset=0", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == word["id"]

    updated = client.patch(
        f"/api/v1/words/{word['id']}",
        headers=headers,
        json={"english": "a house"},
    )
    assert updated.status_code == 200
    assert updated.json()["english"] == "a house"
    assert client.get(f"/api/v1/words/{word['id']}", headers=headers).status_code == 200

    deleted = client.delete(f"/api/v1/words/{word['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/words/{word['id']}", headers=headers).status_code == 404


def test_phrases_and_templates_crud():
    headers = auth()
    phrase = client.post(
        "/api/v1/phrases",
        headers=headers,
        json={"german": "Ich möchte Kaffee", "english": "I would like coffee", "category": "requests"},
    )
    assert phrase.status_code == 201
    phrase_id = phrase.json()["id"]
    assert client.patch(
        f"/api/v1/phrases/{phrase_id}",
        headers=headers,
        json={"category": "polite requests"},
    ).status_code == 200

    template = client.post(
        "/api/v1/templates",
        headers=headers,
        json={"template_text": "Ich möchte {noun}", "translation_hint": "I would like"},
    )
    assert template.status_code == 201
    template_id = template.json()["id"]
    assert client.get("/api/v1/templates", headers=headers).json()["total"] == 1
    assert client.patch(
        f"/api/v1/templates/{template_id}",
        headers=headers,
        json={"translation_hint": "I would like to"},
    ).status_code == 200
    assert client.delete(f"/api/v1/phrases/{phrase_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/templates/{template_id}", headers=headers).status_code == 204


def test_items_are_isolated_between_users_and_require_auth():
    owner_headers = auth()
    other_headers = auth()
    created = client.post(
        "/api/v1/words",
        headers=owner_headers,
        json={"german": "Buch", "english": "book"},
    )
    item_id = created.json()["id"]
    assert client.get(f"/api/v1/words/{item_id}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/v1/words/{item_id}",
        headers=other_headers,
        json={"english": "volume"},
    ).status_code == 404
    assert client.delete(f"/api/v1/words/{item_id}", headers=other_headers).status_code == 404
    assert client.get("/api/v1/words").status_code == 401
