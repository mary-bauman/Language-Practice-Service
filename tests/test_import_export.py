import csv
import io
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": f"csv-{uuid4().hex[:12]}",
            "password": "password-123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_csv_import_and_export_are_owner_scoped():
    headers = auth()
    content = (
        "item_type,german,english,part_of_speech,source,category,"
        "template_text,translation_hint,tags\n"
        'word,Haus,house,noun,,,,,"{""topic"": ""home""}"\n'
        'phrase,Ich möchte Kaffee,I would like coffee,,,requests,,,{}\n'
        'template,,,,,,Ich möchte {noun},I would like,{}\n'
    )
    imported = client.post(
        "/api/v1/data/import.csv",
        headers=headers,
        files={"file": ("items.csv", content, "text/csv")},
    )
    assert imported.status_code == 200
    assert imported.json() == {
        "imported": 3,
        "words": 1,
        "phrases": 1,
        "templates": 1,
    }

    exported = client.get("/api/v1/data/export.csv", headers=headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert {row["item_type"] for row in rows} == {"word", "phrase", "template"}
    assert "Haus" in {row["german"] for row in rows if row["item_type"] == "word"}


def test_csv_import_rejects_bad_input_without_partial_write():
    headers = auth()
    bad_content = (
        "item_type,german,english,part_of_speech,source,category,"
        "template_text,translation_hint,tags\n"
        'word,Gut,good,,,,,{}\n'
        'unknown,Nein,no,,,,,{}\n'
    )
    response = client.post(
        "/api/v1/data/import.csv",
        headers=headers,
        files={"file": ("bad.csv", bad_content, "text/csv")},
    )
    assert response.status_code == 400
    assert client.get("/api/v1/words", headers=headers).json()["total"] == 0


def test_csv_routes_require_auth_and_validate_file_type():
    assert client.get("/api/v1/data/export.csv").status_code == 401
    response = client.post(
        "/api/v1/data/import.csv",
        headers=auth(),
        files={"file": ("items.json", "{}", "application/json")},
    )
    assert response.status_code == 415
