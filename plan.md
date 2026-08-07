# Language Practice Service — Backend Plan

Date: 2026-08-07
Author: Mary (planning document created by Copilot plan agent)

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
- No multi-user access UI (but schema will permit multiple users)

High-level design
-----------------
- API service (HTTP/JSON) with small set of endpoints for words, phrases, templates, and practice events
- Relational database (PostgreSQL recommended) for structured queries, indexing, and easy migration to analytical queries
- Minimal auth (optional token-based) — can be added later; for now local/dev-mode access is fine
- Use an ORM + migrations (e.g., SQLAlchemy + Alembic or Prisma) for maintainability

Data model (suggested tables)
----------------------------
1) users (optional for single-user MVP — include to future-proof)
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
- owner_id (uuid FK users.id, nullable) -- enables multi-user data later

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
- tags, owner_id, created_at, updated_at

5) practice_events (history table)
- id (uuid PK)
- item_type (enum: 'word' | 'phrase' | 'template')
- item_id (uuid FK to appropriate table)
- user_id (uuid FK users.id, nullable)
- attempted_at (timestamp)
- outcome (boolean or enum: 'correct'|'incorrect'|'skipped')
- details (jsonb) -- optional payload (e.g., question text, response latency)

Indexes: (item_type, item_id), user_id, attempted_at

Data model notes
- Keep aggregated counters (total_practices, correct_count) and update them in the same transaction as inserts to practice_events to make reads fast for the frontend.
- Use practice_events as the source-of-truth for analytics; aggregated counters are denormalized for speed.
- Tags as jsonb in Postgres allow flexible filtering and quick extension.

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
  - body: { item_type, item_id, outcome, user_id? , details? }
  - behavior: insert practice_events row; increment counters on words/phrases atomically
- GET /api/v1/practice?item_type=&item_id=&user_id=&since=&until=
  - returns practice history for analytics

Reporting / Analytics (basic)
- GET /api/v1/stats/summary?owner_id=
  - totals: words practiced, total attempts, overall accuracy
- GET /api/v1/stats/word/{id}
  - returns practice history and computed accuracy and streaks

Implementation choices
----------------------
- Language and framework: Python + FastAPI (recommended) or Node.js + Express / NestJS. FastAPI gives quick development, Pydantic models, automatic OpenAPI.
- DB: PostgreSQL (hosted or local for testing)
- ORM: SQLAlchemy + Alembic (Python) or Prisma (Node)
- Testing: pytest (Python) or jest (Node)
- Optional: Dockerfile and docker-compose for local DB + app development

Security and auth
-----------------
- MVP can be kept unauthenticated or with a single API token for personal use.
- If multi-user is added, use JWT or OAuth; ensure owner_id is enforced on queries.
- Validate inputs strictly (Pydantic/JSON schema) to prevent bad data.

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
- Create repository structure and Docker compose with Postgres
- Add initial migration and models for words, phrases, practice_events
- Implement POST /api/v1/practice to ensure correct counter behavior
- Add a seed CSV and one user for local testing

Open questions / decisions
-------------------------
- Single-user vs multi-user now? (Schema included owner_id; decide whether to enforce it now)
- Which tech stack preference (FastAPI vs Node)? (FastAPI recommended)
- Should there be a simple spaced-repetition score stored (e.g., ease factor) or compute externally from events?

If any preferences on the tech stack or single/multi-user direction are provided, the plan will be updated and next steps adjusted.

-- End of plan
