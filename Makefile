.PHONY: setup backend frontend test lint build clean demo-user

PY ?= python3

setup:
	cd backend && $(PY) -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

demo-user:
	cd backend && .venv/bin/python ../scripts/seed_demo_user.py

test:
	cd backend && .venv/bin/python -m pytest

lint:
	cd backend && .venv/bin/ruff check .

build:
	cd frontend && npm run build

clean:
	rm -rf backend/.pytest_cache backend/.ruff_cache frontend/dist
