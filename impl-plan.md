# Implementation Plan — Language Practice Service

Goal
----
Implement the backend described in plan.md (FastAPI + PostgreSQL, multi-user, custom JWT + bcrypt auth, hybrid spaced-repetition model) so the service supports users, words/phrases/templates, practice events, scheduling fields, secure auth, and a recompute path for scheduling migration/repair.

Progress
--------
- Step 1 complete: Docker/FastAPI project scaffold and local health endpoint.
- Step 2 complete: SQLModel schema, PostgreSQL migration, and database session setup.
- Step 3 complete: custom JWT authentication, bcrypt password hashing, refresh-token rotation/revocation, password reset flow, and current-user dependency.
- Step 4 complete: authenticated CRUD and pagination for words, phrases, and sentence templates with ownership isolation.
- Step 5 complete: atomic practice events, SM-2-style scheduling updates, ownership validation, row locking, and concurrency tests.
- Step 6 complete: authenticated owner-scoped scheduler recompute endpoint and idempotent history replay service.

Overview
--------
This document breaks the work into 8 concrete, verifiable steps. Each step includes sub-tasks, expected file artifacts, and how to validate the work locally.

Step 1 — Project scaffold and local dev environment
--------------------------------------------------
What to do
- Create repository layout: app package, tests/, alembic/ (migrations), docker/, scripts/.
- Add Dockerfile and docker-compose.yml that starts the FastAPI app and a Postgres DB for local development. Include a named volume for Postgres data.
- Add a Makefile (or npm-like scripts) with commands: make start, make migrate, make test, make lint.

Key files
- Dockerfile
- docker-compose.yml
- Makefile or scripts/dev.sh
- .env.example with DB_URL, SECRET_KEY, JWT settings

Why this first
- Provides reproducible local environment and makes later steps testable by running against a real DB.

Validation
- Run: docker-compose up --build and verify app responds on configured port (curl localhost:8000/health or auto-generated docs at /docs).

Step 2 — Database schema + migrations
-------------------------------------
What to do
- Choose ORM: SQLModel (built on SQLAlchemy) or SQLAlchemy 2.x with pydantic models. Use Alembic for migrations.
- Implement models and initial Alembic migration for tables: users, refresh_tokens, words, phrases, sentence_templates, practice_events.
- Ensure owner_id and user_id columns are NOT NULL with FK constraints for multi-user enforcement.
- Add scheduling columns on words/phrases/templates: interval_seconds (int), repetitions (int), ease_factor (float), next_due (timestamptz), last_reviewed_at (timestamptz).
- Create indexes: GIN on tags, index on (owner_id, next_due), index on (owner_id, german).

Key files
- app/db/models.py (or app/models/*.py)
- alembic/env.py and versions/0001_initial.py

Why this step
- The schema is the foundation for the rest of the app; migrations let CI and devs apply consistent schemas.

Validation
- Run: make migrate (or alembic upgrade head) and verify tables exist in Postgres (psql -c "\dt").

Step 3 — Auth: users + token storage + middleware
-------------------------------------------------
What to do
- Implement user registration and login with bcrypt (passlib or argon2-cffi). Store password hashes in users table.
- Create refresh_tokens table to store hashed refresh tokens with expiry and session metadata (ip, user_agent optional).
- Implement endpoints: POST /auth/register, POST /auth/login (returns access + refresh), POST /auth/refresh, POST /auth/logout, POST /auth/reset-request, POST /auth/reset-confirm.
- Implement auth middleware (dependency) that validates access JWT, loads the user, and injects current_user into the request context. Do not accept user_id in request bodies for ownership.
- Use environment-provided SECRET_KEY, token TTLs in config (pydantic settings).

Key files
- app/auth/*.py (hashing, token creation, refresh token storage)
- app/api/auth.py (router)
- app/deps.py (current_user dependency)

Why this step
- All subsequent endpoints must be secured and scoped to a user. Implementing auth early lets you enforce owner scoping from the start.

Validation
- Register a user, login, call a protected test endpoint (GET /api/v1/me) using the access token, verify 401 for invalid/expired tokens, and verify refresh flow rotates tokens.

Step 4 — CRUD for words, phrases, templates
-------------------------------------------
What to do
- Implement CRUD endpoints under /api/v1/words, /api/v1/phrases, /api/v1/templates.
- All operations must be scoped by authenticated user (owner_id). Use the current_user dependency to set owner on create and to filter queries (e.g., SELECT ... WHERE owner_id = :user_id).
- Validate inputs with Pydantic models; implement pagination for list endpoints. Implement partial updates (PATCH) safely.

Key files
- app/api/words.py, app/api/phrases.py, app/api/templates.py
- app/schemas/*.py (pydantic request/response models)

Why this step
- The frontend and practice workflows rely on stable CRUD operations to manage items.

Validation
- Use the registered user to create a word, confirm GET /api/v1/words returns only that user's items, and verify unauthorized users cannot access others' items.

Step 5 — Practice events endpoint with atomic updates
-----------------------------------------------------
What to do
- Implement POST /api/v1/practice to record a practice event and update aggregated counters and scheduling fields atomically.
- Transaction pattern: begin transaction → SELECT item FOR UPDATE → INSERT practice_events → compute new scheduling fields (using chosen algorithm) → UPDATE item counters + scheduling fields → commit.
- Handle concurrency with FOR UPDATE or optimistic version column; on conflict, retry a small number of times.
- Ensure practice_events.user_id is set from current_user and item ownership is validated before locking.

Key files
- app/api/practice.py
- app/services/scheduler.py (algorithm implementation, isolated and testable)

Why this step
- This is critical for correctness: history and denormalized fields must remain consistent even under concurrent requests.

Validation
- Write integration tests that spawn two concurrent practice requests for the same item and verify counters and scheduling fields remain consistent and accurate.

Step 6 — Scheduler recompute job and admin API
----------------------------------------------
What to do
- Implement a background job (worker or simple management command) that recomputes scheduling fields from full practice_events history for an owner or globally. This job should be idempotent and resumable.
- Add a protected endpoint for triggering recompute per-user or per-organization: POST /api/v1/scheduler/recompute?owner_id=... (admin-only or owner-scoped).
- Add integrity-check job that periodically verifies denormalized counters against aggregates computed from practice_events and logs or corrects mismatches.

Key files
- app/jobs/recompute.py (script and/or Celery task)
- app/api/admin.py (protected recompute route)

Why this step
- Enables algorithm migration and recovery from drift without manual DB surgery.

Validation
- Seed test data with a changed algorithm and run recompute; confirm stored scheduling fields match recomputed values.

Step 7 — Import/export, seed data, and CLI utilities
----------------------------------------------------
What to do
- Implement CSV import/export for words/phrases with ownership mapping (assign owner during import).
- Add seed scripts to create test users and seed example vocab/phrases/templates.
- Provide a CLI script (scripts/seed.py) that runs inside the Docker development container for easy local setup.

Key files
- app/utils/import_export.py
- scripts/seed.py

Why this step
- Makes getting a local dev environment with sample data trivial and supports migration of existing vocab lists.

Validation
- Run the seed script and confirm sample words and a test user exist; run export to CSV and verify contents.
- Implemented: authenticated transactional CSV import/export, idempotent sample seed script,
  Docker Makefile target, and API tests. Full suite passes with 97% coverage.

Step 8 — Tests, CI, docs, and observability
------------------------------------------
What to do
- Write unit tests for models, scheduler logic, and auth. Write integration tests for API endpoints using pytest + httpx + an ephemeral Postgres (docker-compose or testcontainers).
- Add a GitHub Actions workflow (or other CI) that runs lint, tests, and migrations against a test database on push/PR.
- Add OpenAPI docs (auto from FastAPI) and a README with setup steps (docker-compose, migrations, seed, test commands).
- Add basic metrics/logging (structured JSON logs, request IDs), and an endpoint GET /health and GET /metrics (optional Prometheus).

Key files
- tests/ (unit + integration)
- .github/workflows/ci.yml
- README.md (setup & developer guide)

Why this step
- Ensures quality, reproducibility, and makes onboarding easier. CI keeps regressions out.

Validation
- Push a branch and verify CI runs; locally run pytest and ensure all tests pass.

Notes on prioritization and minimal path
---------------------------------------
If time-constrained, prioritize the following minimal path to have a usable backend:
1. Steps 1, 2 (minimal schema), 3 (auth essentials), 4 (CRUD), 5 (practice with a simple algorithm).
2. Add Step 6 recompute and Step 7 import/export soon after.
3. Step 8 (CI, extensive tests, observability) can be started in parallel but keep a small core test suite to protect correctness.

Estimated timeline (rough)
- Scaffold + DB + basic auth: 1-2 days
- CRUD endpoints + tests: 1-2 days
- Practice endpoint (atomic) + scheduler basic: 1 day
- Recompute job + import/export + polishing: 1-2 days
- Tests and CI: 1-2 days

Next action suggestion
----------------------
Pick which step to scaffold first (scaffold project + docker-compose is recommended) and the implementation will be created: Dockerfile, docker-compose.yml, initial FastAPI app, and a minimal alembic migration that creates the users table.
