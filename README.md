# InsightAI

A business finance assistant for Indian small-business owners and startup founders, extending the ideas in SentifyAI. This repository starts a clean, smaller implementation; the original Downloads folder is untouched. Existing SentifyAI market/news functions have been reviewed but have **not** been migrated yet.

## Working in this milestone

- SvelteKit/TypeScript dashboard with registration, login and one business workspace per owner.
- FastAPI with Argon2 password hashing and short-lived JWT bearer authentication. The web client keeps its token in memory, not browser storage; page refresh signs you out.
- Business-scoped document upload, listing, source-text inspection, duplicate detection and retry after processing failure.
- Text extraction for UTF-8 CSV, XLSX, XLS, text PDF and DOCX with source locations. PDF/Office/image signatures and Office archive expansion limits are checked. File formats have explicit support boundaries.
- Images and scanned PDFs are accepted and marked `needs_attention`: OCR is **not enabled**. Extracted text is explicitly unverified and never silently converted into accounting records.
- SQLAlchemy/Alembic schema; local file storage or private S3 adapter; Celery/Redis worker configuration; Docker Compose with PostgreSQL/pgvector, API, worker and web.

## Local quick start

Use Python 3.12 and Node.js 22 for a consistent environment. From the repository root:

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -e 'backend[test]'
cp backend/.env.example backend/.env
```

Generate a secret with `openssl rand -hex 32`, and put it in `backend/.env` as `JWT_SECRET`. The placeholder is intentionally rejected. Keep `TASK_MODE=inline` for a local run without Redis. Inline extraction blocks the upload request and is development-only.

`backend/requirements-dev.lock` records the tested Python 3.12 dependency versions. To reproduce those versions, install it from `backend` using `.venv/bin/pip install -r requirements-dev.lock`, then `.venv/bin/pip install --no-deps -e .`. The frontend uses `package-lock.json`. Use Node 22.12 or newer; the system's older Node may fail with Vite 7.

In one terminal:

```sh
cd backend
mkdir -p data
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. API docs are at http://127.0.0.1:8000/docs. Register a workspace, then upload a CSV or spreadsheet and inspect the extracted text. No API keys are required for this milestone.

## Docker development stack

Copy `.env.example` to `.env` at the repository root. Set `JWT_SECRET` and `POSTGRES_PASSWORD` to **different** generated hexadecimal secrets. Start Docker Desktop, then:

```sh
docker compose up --build
```

Open http://localhost:3000. A one-shot migration service initializes PostgreSQL before the API and worker start. Uploads are shared through a named volume. Database and Redis ports are not published; web/API ports bind to localhost. This is a development configuration, not a public production deployment.

For local Celery testing, start Redis, set `TASK_MODE=celery` and the correct `REDIS_URL` in `backend/.env`, then run `.venv/bin/celery -A app.tasks.celery worker --loglevel=info` from `backend` alongside the API.

## Checks

```sh
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests migrations
```

```sh
cd frontend
npm run check
npm run build
```

The backend tests use temporary SQLite databases and local storage. They check authentication, business isolation, upload validation, duplicate handling, spreadsheet source references and retry after a queue failure. PostgreSQL, Redis and S3 integration need separate checks with those services running.

## Architecture and next work

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for decisions and scope. The immediate next milestone is structured extraction review and deterministic financial records/calculations. AI chat, embeddings, LangGraph execution, OCR, Indian news retrieval and calendar actions are not implemented yet. Optional `agents` and `ocr` dependency groups reserve those integrations without loading large dependencies into the basic app.

Before public deployment: add email verification, password reset, login/signup throttling, HTTPS/edge request limits, storage quotas, audit/retention controls, malware scanning and isolated document workers. Add queue recovery for interrupted workers, PostgreSQL/Redis/S3 integration tests and tested backup/restore. Hosting app data in India does not automatically place future model/provider processing in India.

Source review: [PROJECT_REVIEW.md](PROJECT_REVIEW.md). Retain SentifyAI attribution and its license when migrating its source into this repository.
