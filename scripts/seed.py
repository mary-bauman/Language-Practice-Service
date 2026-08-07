import argparse
import sys

from sqlmodel import select

sys.path.insert(0, ".")

from app.auth.security import hash_password
from app.db.models import Phrase, SentenceTemplate, User, Word
from app.db.session import get_session


def seed(username: str, password: str) -> None:
    session = next(get_session())
    try:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            user = User(username=username, password_hash=hash_password(password))
            session.add(user)
            session.commit()
            session.refresh(user)

        existing_word = session.exec(
            select(Word).where(
                Word.owner_id == user.id, Word.german == "Hallo"
            )
        ).first()
        if existing_word is None:
            session.add_all(
                [
                    Word(german="Hallo", english="Hello", owner_id=user.id),
                    Phrase(
                        german="Ich möchte Kaffee",
                        english="I would like coffee",
                        category="requests",
                        owner_id=user.id,
                    ),
                    SentenceTemplate(
                        template_text="Ich möchte {noun}",
                        translation_hint="I would like",
                        owner_id=user.id,
                    ),
                ]
            )
            session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed local language-practice data")
    parser.add_argument("--username", default="seed-user")
    parser.add_argument("--password", default="password-123")
    args = parser.parse_args()
    seed(args.username, args.password)
    print(f"Seeded user and sample data for {args.username}")
