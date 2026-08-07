from typing import Any, Dict, Type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db.models import Phrase, SentenceTemplate, User, Word
from app.db.session import get_session
from app.deps import get_current_user
from app.schemas.items import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    Page,
    PhraseCreate,
    PhraseResponse,
    PhraseUpdate,
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)


def _get_owned(session: Session, model: Type[Any], item_id: UUID, user_id: UUID):
    item = session.get(model, item_id)
    if item is None or item.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _page(session: Session, model: Type[Any], user_id: UUID, limit: int, offset: int):
    query = select(model).where(model.owner_id == user_id)
    items = session.exec(query.offset(offset).limit(limit)).all()
    total = len(session.exec(select(model).where(model.owner_id == user_id)).all())
    return items, total


router = APIRouter(tags=["items"])


@router.post("/words", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_word(
    payload: ItemCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = Word(**payload.dict(), owner_id=current_user.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/words", response_model=Page[ItemResponse])
def list_words(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items, total = _page(session, Word, current_user.id, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/words/{item_id}", response_model=ItemResponse)
def get_word(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return _get_owned(session, Word, item_id, current_user.id)


@router.patch("/words/{item_id}", response_model=ItemResponse)
def update_word(
    item_id: UUID,
    payload: ItemUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = _get_owned(session, Word, item_id, current_user.id)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/words/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_word(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = _get_owned(session, Word, item_id, current_user.id)
    session.delete(item)
    session.commit()


@router.post("/phrases", response_model=PhraseResponse, status_code=status.HTTP_201_CREATED)
def create_phrase(
    payload: PhraseCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = Phrase(**payload.dict(), owner_id=current_user.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/phrases", response_model=Page[PhraseResponse])
def list_phrases(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items, total = _page(session, Phrase, current_user.id, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/phrases/{item_id}", response_model=PhraseResponse)
def get_phrase(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return _get_owned(session, Phrase, item_id, current_user.id)


@router.patch("/phrases/{item_id}", response_model=PhraseResponse)
def update_phrase(
    item_id: UUID,
    payload: PhraseUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = _get_owned(session, Phrase, item_id, current_user.id)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/phrases/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phrase(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = _get_owned(session, Phrase, item_id, current_user.id)
    session.delete(item)
    session.commit()


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = SentenceTemplate(**payload.dict(), owner_id=current_user.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/templates", response_model=Page[TemplateResponse])
def list_templates(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items, total = _page(session, SentenceTemplate, current_user.id, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/templates/{item_id}", response_model=TemplateResponse)
def get_template(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return _get_owned(session, SentenceTemplate, item_id, current_user.id)


@router.patch("/templates/{item_id}", response_model=TemplateResponse)
def update_template(
    item_id: UUID,
    payload: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = _get_owned(session, SentenceTemplate, item_id, current_user.id)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/templates/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = _get_owned(session, SentenceTemplate, item_id, current_user.id)
    session.delete(item)
    session.commit()
