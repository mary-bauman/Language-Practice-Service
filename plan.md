# Language Practice Service — Backend Plan

Date: 2026-08-07
Author: Mary (planning document created by Copilot plan agent)

Implementation status
---------------------
- Steps 1-4 complete: project scaffold, database schema/migrations, custom JWT authentication, and user-scoped CRUD.
- Step 5 complete: atomic practice-event recording, aggregate counters, scheduling updates, ownership checks, and row locking.
- Step 6 complete: owner-scoped scheduling recomputation from immutable history with idempotent repair behavior.
- Step 7 complete: authenticated transactional CSV import/export and idempotent seed-data CLI.
- Step 8 complete: CI, documentation, and observability are implemented and validated.

Purpose
-------
This document describes the plan for a backend service to store German vocabulary and phrase practice data. The service's goals:
- Efficiently store words, phrases, and sentence-construction templates.
- Record practice attempts (counts, correctness, timestamps) so progress and analytics can be derived.
- Provide a simple REST API for a future frontend and import/export capabilities.

Scope (MVP)
-----------
- Persistent storage of vocabulary words (German + English) and phrases
- Tracking of practice metrics per item (times practiced, times correct)
- Recording practice-history events (timestamped results)
- Basic REST API to create/read/update items and to record practice attempts
- Data model designed to support later features: per-user data, spaced repetition, analytics, tagging

Non-goals for MVP
-----------------
- No frontend in this phase
- No advanced repetition algorithm (initially store counts; algorithm can be built on top later)
- No multi-user access UI (frontend) — the backend will enforce multi-user support (owner_id) and access control in the MVP.

High-level design
-----------------
- API service (HTTP/JSON) with small set of endpoints for words, phrases, templates, and practice events
- Relational database (PostgreSQL recommended) for structured queries, indexing, and easy migration to analytical queries
- Auth required for multi-user support: implement JWT-based authentication and enforce owner scoping on all resources. Local/dev mode may allow a dev token, but production requires proper auth.
- Use an ORM + migrations (e.g., SQLAlchemy + Alembic or Prisma) for maintainability

Data model (suggested tables)
----------------------------
1) users (required for multi-user MVP; authentication and ownership enforced)
- id (uuid PK)
- username (text, unique)
- created_at, updated_at

2) words
- id (uuid PK)
- german (text) -- canonical form (lowercase normalized)
- english (text)
- part_of_speech (text, optional)
- source (text, optional) -- where the word came from
- tags (jsonb or text[]) -- e.g., ["food","travel"]
- total_practices (int, default 0)
- correct_count (int, default 0)
- last_practiced_at (timestamp, nullable)
- created_at, updated_at
- owner_id (uuid FK users.id, not nullable) -- owner required; all records belong to a user and queries must be scoped by owner.

Indexes: index on (owner_id, german), last_practiced_at, tags (GIN for jsonb/text[])

3) phrases
- id (uuid PK)
- german (text)
- english (text)
- category (text, e.g., "Ich möchte" templates)
- tags (jsonb/text[])
- total_practices, correct_count, last_practiced_at
- created_at, updated_at
- owner_id (uuid FK)

4) sentence_templates (for storing constructions like "Ich möchte ...")
- id (uuid PK)
- template_text (text) -- e.g., "Ich möchte {verb_phrase}"
- translation_hint (text) -- e.g., "I would like"
- examples_count (int)
- tags, owner_id (uuid FK users.id, not nullable), created_at, updated_at

5) practice_events (history table)
- id (uuid PK)
- item_type (enum: 'word' | 'phrase' | 'template')
- item_id (uuid FK to appropriate table)
- user_id (uuid FK users.id, not nullable) -- derived from authentication; practice events must be associated with a user.
- attempted_at (timestamp)
- outcome (boolean or enum: 'correct'|'incorrect'|'skipped')
- details (jsonb) -- optional payload (e.g., question text, response latency)

Indexes: (item_type, item_id), user_id, attempted_at

Data model notes
- Owner enforcement: owner_id is required on words, phrases, templates and must be enforced both by the application layer and database constraints (FK + NOT NULL). All queries and updates must be scoped by owner/user.
- Keep aggregated counters (total_practices, correct_count) and update them in the same transaction as inserts to practice_events to make reads fast for the frontend.
- Use practice_events as the source-of-truth for analytics; aggregated counters are denormalized for speed and can be recomputed from history when needed.
- Tags as jsonb in Postgres allow flexible filtering and quick extension. Use GIN indexes for efficient tag searches.

API Surface (MVP)
------------------
Base: /api/v1

Words
- POST /api/v1/words
  - body: { german, english, part_of_speech?, tags? }
  - returns: created word
- GET /api/v1/words?tag=&limit=&offset=&search=
  - returns list with pagination
- GET /api/v1/words/{id}
- PATCH /api/v1/words/{id}
  - partial updates
- DELETE /api/v1/words/{id}

Phrases
- same CRUD endpoints under /api/v1/phrases

Templates
- CRUD under /api/v1/templates
- GET /api/v1/templates/{id}/examples  -- optional endpoint to list example phrases

Practice events
- POST /api/v1/practice
  - body: { item_type, item_id, outcome, details? }  (authenticated user is derived from the JWT)
  - behavior: insert practice_events row with the authenticated user; increment counters on words/phrases atomically and scoped to the owner.
- GET /api/v1/practice?item_type=&item_id=&user_id=&since=&until=
  - returns practice history for analytics

Reporting / Analytics (basic)
- GET /api/v1/stats/summary?owner_id=
  - totals: words practiced, total attempts, overall accuracy
- GET /api/v1/stats/word/{id}
  - returns practice history and computed accuracy and streaks

Implementation choices
----------------------
- Language and framework: Python + FastAPI (Pydantic models, async support, automatic OpenAPI) — chosen for this project.
- DB: PostgreSQL (hosted or local for testing)
- ORM and migrations: SQLAlchemy (or SQLModel) + Alembic for migrations and schema evolution
- Auth libraries: fastapi-users or custom FastAPI + PyJWT for JWT handling and password hashing (bcrypt)
- Testing: pytest + httpx for API integration tests
- Dev tooling: Dockerfile and docker-compose for local Postgres + app development; use testcontainers or ephemeral Postgres in CI for integration tests

Security and auth
-----------------
- Authentication required in the MVP: use JWT-based auth (e.g., fastapi-users or custom implementation using PyJWT) with secure password hashing (bcrypt/argon2).
- All resources are owned by users: owner_id/user_id must be enforced by the database (FK + NOT NULL) and by application-layer checks so no user can access another user's data.
- API should derive the user from the JWT (do not accept user_id in request bodies for ownership-sensitive endpoints).
- Use HTTPS in production and ensure strong token handling (short token lifetime + refresh tokens if needed). Validate inputs strictly with Pydantic to prevent bad data.

Migrations and data
-------------------
- Use a migration system (Alembic, Prisma migrations) from the start so schema evolves cleanly.
- Provide a small seed script to add a few example words/phrases and an admin user for testing.
- Support CSV import/export for migrating existing vocab lists.

Performance considerations
-------------------------
- Reads for the frontend will favor aggregated counters; keep counters updated in the same DB transaction as practice_events to avoid drift.
- Add indexes for typical filters: tag searches, recently practiced, owner scope.
- For large history datasets, use partitioning on practice_events by time or archive old events.

Testing plan
------------
- Unit tests for models and services (CRUD, practice event processing)
- Integration tests with an ephemeral Postgres (docker-compose or testcontainers)
- API tests exercising the endpoints and concurrency for updating counters

Milestones (concrete)
---------------------
1) Project scaffold (1 day)
   - repo, basic app skeleton, Dockerfile, docker-compose with Postgres
   - create migrations and initial schema
2) Core models & CRUD (2 days)
   - Implement words, phrases, templates tables and CRUD endpoints
   - Add simple validations
3) Practice events (1 day)
   - Create practice_events endpoint and atomic counter updates
   - Add tests
4) Import/export & seed data (0.5 day)
   - CSV import and export
5) Basic analytics endpoints + docs (0.5 day)
   - Summary and item-level stats
6) Polish & small refactors (1 day)
   - Logging, error handling, README, deploy instructions

Next steps (immediate)
----------------------
- Create repository structure and Docker compose with Postgres.
- Add initial migration and models for users, words, phrases, templates, and practice_events; make owner/user required where applicable.
- Implement authentication: user registration, login (JWT), and middleware to derive the authenticated user from requests.
- Implement CRUD for words/phrases/templates scoped to the authenticated user.
- Implement POST /api/v1/practice to record events and atomically update counters (derived from the authenticated user).
- Add seed CSV and seed users (at least one test user) for local testing and CI.

Open questions / decisions
-------------------------
- Spaced-repetition approach (decided): Hybrid — store denormalized scheduling fields per item for fast "due" queries while keeping practice_events as the immutable source-of-truth. Concretely:
  - Schema additions per item: interval_seconds (int), repetitions (int), ease_factor (float), next_due (timestamptz), last_reviewed_at (timestamptz), optional version/updated_at for optimistic concurrency. Create index: (owner_id, next_due).
  - Atomic update pattern: in POST /api/v1/practice, insert practice_events and update aggregated counters + scheduling fields in a single DB transaction. Use SELECT ... FOR UPDATE on the item row (or optimistic version retry) to prevent races.
  - Recompute/migration path: provide a protected background job or API endpoint (e.g., POST /api/v1/admin/recompute-scheduling or POST /api/v1/scheduler/recompute for per-user) that rebuilds scheduling fields from full history after algorithm changes or to repair drift. Make the job idempotent.
  - Testing & monitoring: unit tests for algorithm, integration tests for concurrent updates, periodic integrity checks that compare aggregates against practice_events and optionally auto-correct or flag discrepancies.
  - API note: practice requests must derive user from JWT (do not accept user_id in body) and validate ownership before updating the item.
- Auth library decision: use a custom lightweight JWT + bcrypt implementation for full control over authentication, token lifecycle, and security policies. Implementation notes:
  - Passwords: store salted bcrypt hashes (or argon2) with a work factor configured for server hardware; provide password-reset flow.
  - Tokens: use short-lived access JWTs (e.g., 15m) signed with an asymmetric keypair (RS256) or HMAC (HS256) if simpler. Provide refresh tokens with longer lifetime (e.g., 7-30 days).
  - Refresh token handling: store refresh tokens (hashed) in DB per user/session to allow revocation and rotation. Issue a new access token + rotated refresh token on use.
  - Revocation: support per-session revocation by removing stored refresh token; maintain a lightweight token blacklist for critical events (password reset). Keep blacklist expiration aligned with token TTLs.
  - Endpoints: POST /auth/register, POST /auth/login (returns access+refresh), POST /auth/refresh (rotate refresh token), POST /auth/logout (revoke refresh token), POST /auth/reset-request, POST /auth/reset-confirm.
  - Middleware: derive user from Authorization: Bearer <access_token>, validate signature/exp/iss/aud claims, and inject current_user into request context. Do not accept user_id in request bodies for ownership-sensitive actions.
  - Security: use HTTPS in production, enforce strong CORS, rate-limit auth endpoints, log suspicious attempts, rotate signing keys periodically, and store secrets securely (env or secret manager).
  - Libraries: use python-jose or PyJWT for JWT handling, passlib/bcrypt or argon2-cffi for hashing, and pydantic for request validation. Wrap low-level crypto in a small auth module to keep the rest of the app framework-agnostic.

If any preferences on the tech stack or single/multi-user direction are provided, the plan will be updated and next steps adjusted.

-- End of plan
