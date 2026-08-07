from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_register_login_me_and_refresh_rotation():
    username = f"user-{uuid4().hex[:12]}"
    password = "correct horse battery staple"

    registered = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    assert registered.status_code == 201
    tokens = registered.json()
    assert tokens["token_type"] == "bearer"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == username

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert logged_in.status_code == 200
    login_tokens = logged_in.json()

    rotated = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != login_tokens["refresh_token"]

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert reused.status_code == 401


def test_protected_endpoint_rejects_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
