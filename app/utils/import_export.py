import csv
import io
import json
from typing import Dict, Iterable, List, Tuple, Type

from pydantic import ValidationError
from sqlmodel import Session, select

from app.db.models import Phrase, SentenceTemplate, User, Word
from app.schemas.items import ItemCreate, PhraseCreate, TemplateCreate

ITEM_MODELS: Dict[str, Type] = {
    "word": Word,
    "phrase": Phrase,
    "template": SentenceTemplate,
}
CSV_FIELDS = [
    "item_type",
    "german",
    "english",
    "part_of_speech",
    "source",
    "category",
    "template_text",
    "translation_hint",
    "tags",
]


def export_items(session: Session, user: User) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for item_type, model in ITEM_MODELS.items():
        items = session.exec(
            select(model).where(model.owner_id == user.id)
        ).all()
        for item in items:
            writer.writerow(
                {
                    "item_type": item_type,
                    "german": getattr(item, "german", ""),
                    "english": getattr(item, "english", ""),
                    "part_of_speech": getattr(item, "part_of_speech", ""),
                    "source": getattr(item, "source", ""),
                    "category": getattr(item, "category", ""),
                    "template_text": getattr(item, "template_text", ""),
                    "translation_hint": getattr(item, "translation_hint", ""),
                    "tags": json.dumps(item.tags or {}, ensure_ascii=False),
                }
            )
    return output.getvalue()


def _parse_tags(raw: str) -> dict:
    if not raw.strip():
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("tags must be a JSON object")
    return parsed


def import_items(session: Session, user: User, content: str) -> Dict[str, int]:
    reader = csv.DictReader(io.StringIO(content))
    missing = set(CSV_FIELDS) - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

    pending: List[object] = []
    errors: List[str] = []
    for line_number, row in enumerate(reader, start=2):
        item_type = (row.get("item_type") or "").strip()
        try:
            tags = _parse_tags(row.get("tags") or "")
            if item_type == "word":
                payload = ItemCreate(
                    german=row.get("german") or "",
                    english=row.get("english") or None,
                    part_of_speech=row.get("part_of_speech") or None,
                    source=row.get("source") or None,
                    tags=tags,
                )
                pending.append(Word(**payload.dict(), owner_id=user.id))
            elif item_type == "phrase":
                payload = PhraseCreate(
                    german=row.get("german") or "",
                    english=row.get("english") or None,
                    category=row.get("category") or None,
                    tags=tags,
                )
                pending.append(Phrase(**payload.dict(), owner_id=user.id))
            elif item_type == "template":
                payload = TemplateCreate(
                    template_text=row.get("template_text") or "",
                    translation_hint=row.get("translation_hint") or None,
                    tags=tags,
                )
                pending.append(SentenceTemplate(**payload.dict(), owner_id=user.id))
            else:
                raise ValueError("item_type must be word, phrase, or template")
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            errors.append(f"line {line_number}: {exc}")

    if errors:
        raise ValueError("; ".join(errors))
    session.add_all(pending)
    session.commit()
    return {
        "imported": len(pending),
        "words": sum(isinstance(item, Word) for item in pending),
        "phrases": sum(isinstance(item, Phrase) for item in pending),
        "templates": sum(isinstance(item, SentenceTemplate) for item in pending),
    }
