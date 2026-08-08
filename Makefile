.PHONY: start migrate seed test lint build

start:
	@docker-compose up --build

build:
	@docker-compose build

migrate:
	@alembic upgrade head

seed:
	@python scripts/seed.py

test:
	@pytest --cov=app --cov-report=term-missing --cov-fail-under=90 -q

lint:
	@ruff check --select E9,F63,F7,F82 app tests
