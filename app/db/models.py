from __future__ import annotations
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(index=True, nullable=False, unique=True)
    email: Optional[EmailStr] = Field(default=None, index=True, unique=True)
    password_hash: str
    reset_token_hash: Optional[str] = None
    reset_token_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RefreshToken(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    token_hash: str  # hashed refresh token
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    revoked: bool = Field(default=False)


class BaseItem(SQLModel):
    german: str
    english: Optional[str] = None
    part_of_speech: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    total_practices: int = 0
    correct_count: int = 0
    last_practiced_at: Optional[datetime] = None
    # scheduling fields (hybrid approach)
    interval_seconds: Optional[int] = None
    repetitions: int = 0
    ease_factor: float = 2.5
    next_due: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None


class Word(BaseItem, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    german: str = Field(index=True, nullable=False)
    owner_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)


class Phrase(BaseItem, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    german: str = Field(nullable=False)
    category: Optional[str] = None
    owner_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)


class SentenceTemplate(BaseItem, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    template_text: str = Field(nullable=False)
    translation_hint: Optional[str] = None
    examples_count: int = 0
    owner_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)


class PracticeEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    item_type: str = Field(nullable=False)  # 'word' | 'phrase' | 'template'
    item_id: UUID = Field(nullable=False, index=True)
    user_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    attempted_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    outcome: str = Field(nullable=False)  # 'correct'|'incorrect'|'skipped'
    details: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
