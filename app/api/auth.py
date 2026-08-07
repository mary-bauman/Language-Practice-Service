from datetime import datetime, timedelta
import secrets
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, select

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.db.models import RefreshToken, User
from app.db.session import get_session
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    email: Optional[EmailStr] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class ResetRequest(BaseModel):
    username: str


class ResetConfirmRequest(BaseModel):
    username: str
    reset_token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _issue_tokens(session: Session, user: User) -> TokenResponse:
    raw_refresh = create_refresh_token()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_opaque_token(raw_refresh),
        expires_at=datetime.utcnow()
        + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(refresh)
    session.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=raw_refresh,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.username == payload.username)).first():
        raise HTTPException(status_code=409, detail="Username already registered")
    if payload.email and session.exec(select(User).where(User.email == payload.email)).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _issue_tokens(session, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return _issue_tokens(session, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)):
    token_hash = hash_opaque_token(payload.refresh_token)
    stored = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).first()
    if (
        stored is None
        or stored.revoked
        or stored.expires_at is None
        or stored.expires_at <= datetime.utcnow()
    ):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = session.get(User, stored.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    stored.revoked = True
    session.add(stored)
    session.commit()
    return _issue_tokens(session, user)


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    stored = session.exec(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_opaque_token(payload.refresh_token),
            RefreshToken.user_id == current_user.id,
        )
    ).first()
    if stored:
        stored.revoked = True
        session.add(stored)
        session.commit()


@router.post("/reset-request")
def reset_request(payload: ResetRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    response = {"message": "If the account exists, a reset token was generated"}
    if user is None:
        return response
    raw_token = secrets.token_urlsafe(32)
    user.reset_token_hash = hash_opaque_token(raw_token)
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
    session.add(user)
    session.commit()
    if settings.expose_reset_tokens:
        response["reset_token"] = raw_token
    return response


@router.post("/reset-confirm")
def reset_confirm(payload: ResetConfirmRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if (
        user is None
        or user.reset_token_hash != hash_opaque_token(payload.reset_token)
        or user.reset_token_expires_at is None
        or user.reset_token_expires_at <= datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.password_hash = hash_password(payload.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    session.add(user)
    session.commit()
    return {"message": "Password reset successfully"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
    }
