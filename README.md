# Language Practice Service (Backend)

FastAPI + PostgreSQL backend to track German vocabulary, phrases, and practice history (multi-user).

Quickstart (Docker)
1. cp .env.example .env
2. docker-compose up --build
3. Open http://localhost:8000/docs (health: /api/v1/health)

Run locally (venv)
1. python -m venv .venv && source .venv/bin/activate
2. pip install -r requirements.txt
3. cp .env.example .env && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Migrations
Configure alembic/env.py to import your models' metadata and set sqlalchemy.url, then:

    alembic upgrade head

Tests
pytest -q

See plan.md and impl-plan.md for roadmap and implementation details.
