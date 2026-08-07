.PHONY: start migrate test lint build

start:
	@docker-compose up --build

build:
	@docker-compose build

migrate:
	@echo "Run migrations (not yet implemented): alembic upgrade head"

test:
	@pytest -q

lint:
	@echo "Run linting (not configured)"
