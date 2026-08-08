from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import JWTError, jwt
from sqlmodel import select

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_opaque_token,
)
from app.config import settings
from app.db.models import RefreshToken
from app.db.session import get_session
from app.main import app


client = TestClient(app)


def register(username=None, email=None):
    username = username or f"user-{uuid4().hex[:12]}"
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "password-123"},
    )
    assert response.status_code == 201
    return username, response.json()


def test_duplicate_username_and_email_are_rejected():
    username, _ = register()
    duplicate_username = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password-123"},
    )
    assert duplicate_username.status_code == 409

    email = f"{uuid4().hex}@example.com"
    register(email=email)
    duplicate_email = client.post(
        "/api/v1/auth/register",
        json={"username": f"user-{uuid4().hex[:12]}", "email": email, "password": "password-123"},
    )
    assert duplicate_email.status_code == 409


def test_invalid_login_and_refresh_are_rejected():
    username, _ = register()
    bad_password = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrong-password"},
    )
    assert bad_password.status_code == 401
    missing_user = client.post(
        "/api/v1/auth/login",
        json={"username": "does-not-exist", "password": "wrong-password"},
    )
    assert missing_user.status_code == 401
    invalid_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "x" * 20},
    )
    assert invalid_refresh.status_code == 401


def test_logout_revokes_refresh_token_and_ignores_unknown_token():
    _, tokens = register()
    access = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=access,
    ).status_code == 204
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "y" * 20},
        headers=access,
    ).status_code == 204


def test_password_reset_request_and_confirmation():
    username, _ = register()
    previous = settings.expose_reset_tokens
    settings.expose_reset_tokens = True
    try:
        missing = client.post(
            "/api/v1/auth/reset-request",
            json={"username": "missing-user"},
        )
        assert missing.status_code == 200
        generated = client.post(
            "/api/v1/auth/reset-request",
            json={"username": username},
        )
        reset_token = generated.json()["reset_token"]
        confirmed = client.post(
            "/api/v1/auth/reset-confirm",
            json={
                "username": username,
                "reset_token": reset_token,
                "new_password": "new-password-123",
            },
        )
        assert confirmed.status_code == 200
        assert client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "new-password-123"},
        ).status_code == 200
        invalid = client.post(
            "/api/v1/auth/reset-confirm",
            json={
                "username": username,
                "reset_token": reset_token,
                "new_password": "another-password",
            },
        )
        assert invalid.status_code == 400
    finally:
        settings.expose_reset_tokens = previous


def test_expired_refresh_token_and_missing_user_token():
    _, tokens = register()
    session = next(get_session())
    try:
        stored = session.exec(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_opaque_token(tokens["refresh_token"])
            )
        ).first()
        stored.expires_at = datetime.utcnow() - timedelta(minutes=1)
        session.add(stored)
        session.commit()
    finally:
        session.close()
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 401

    _, valid_tokens = register()
    with patch("app.api.auth.Session.get", return_value=None):
        assert client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": valid_tokens["refresh_token"]},
        ).status_code == 401

    token = create_access_token(str(uuid4()))
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 401


def test_invalid_access_token_claims_are_rejected():
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(JWTError, match="invalid access token"):
        decode_access_token(token)
