from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class PracticeRequest(BaseModel):
    item_type: str
    item_id: UUID
    outcome: str
    details: Optional[Dict[str, object]] = None

    @validator("item_type")
    def valid_item_type(cls, value: str) -> str:
        if value not in {"word", "phrase", "template"}:
            raise ValueError("item_type must be word, phrase, or template")
        return value

    @validator("outcome")
    def valid_outcome(cls, value: str) -> str:
        if value not in {"correct", "incorrect", "skipped"}:
            raise ValueError("outcome must be correct, incorrect, or skipped")
        return value


class PracticeResponse(BaseModel):
    id: UUID
    item_type: str
    item_id: UUID
    user_id: UUID
    attempted_at: datetime
    outcome: str
    details: Optional[Dict[str, object]]

    class Config:
        orm_mode = True
