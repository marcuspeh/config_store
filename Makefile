.PHONY: help dev-backend dev-frontend build test lint clean

help:
	@echo "Targets:"
	@echo "  dev-backend   - Run backend + dependencies via docker compose"
	@echo "  dev-frontend  - Run frontend dev server (once scaffolded)"
	@echo "  build         - Build both docker images"
	@echo "  test          - Run backend tests"
	@echo "  lint          - Lint backend"
	@echo "  clean         - Remove build/cache artifacts"

dev-backend:
	cd backend && docker compose up

dev-frontend:
	cd frontend && pnpm dev

build:
	docker build -t config_store ./backend
	docker build -t config_store_frontend ./frontend

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .

clean:
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
	rm -rf frontend/node_modules frontend/.next
	find . -type d -name __pycache__ -exec rm -rf {} +
