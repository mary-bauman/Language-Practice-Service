from datetime import datetime
from typing import Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ItemBase(BaseModel):
    german: str = Field(min_length=1, max_length=500)
    english: Optional[str] = Field(default=None, max_length=500)
    part_of_speech: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[Dict[str, str]] = None

    @validator("german")
    def german_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("german must not be blank")
        return value


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    german: Optional[str] = Field(default=None, min_length=1, max_length=500)
    english: Optional[str] = Field(default=None, max_length=500)
    part_of_speech: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[Dict[str, str]] = None

    @validator("german")
    def german_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("german must not be blank")
        return value


class PhraseCreate(ItemBase):
    category: Optional[str] = Field(default=None, max_length=100)


class PhraseUpdate(ItemUpdate):
    category: Optional[str] = Field(default=None, max_length=100)


class TemplateCreate(BaseModel):
    template_text: str = Field(min_length=1, max_length=500)
    translation_hint: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[Dict[str, str]] = None

    @validator("template_text")
    def template_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("template_text must not be blank")
        return value


class TemplateUpdate(BaseModel):
    template_text: Optional[str] = Field(default=None, min_length=1, max_length=500)
    translation_hint: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[Dict[str, str]] = None

    @validator("template_text")
    def template_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("template_text must not be blank")
        return value


class ItemResponse(ItemBase):
    id: UUID
    owner_id: UUID
    total_practices: int
    correct_count: int
    last_practiced_at: Optional[datetime]
    interval_seconds: Optional[int]
    repetitions: int
    ease_factor: float
    next_due: Optional[datetime]
    last_reviewed_at: Optional[datetime]

    class Config:
        orm_mode = True


class PhraseResponse(ItemResponse):
    category: Optional[str]


class TemplateResponse(BaseModel):
    id: UUID
    owner_id: UUID
    template_text: str
    translation_hint: Optional[str]
    tags: Optional[Dict[str, str]]
    examples_count: int
    interval_seconds: Optional[int]
    repetitions: int
    ease_factor: float
    next_due: Optional[datetime]
    last_reviewed_at: Optional[datetime]

    class Config:
        orm_mode = True


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int
