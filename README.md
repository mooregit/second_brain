# Second Brain Inbox

Local-first inbox for turning raw notes into structured memories, tasks, decisions, questions, graph nodes, and grounded answers.

## Stack

- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic, Ollama HTTP API
- Frontend: React, Vite, Tailwind, React Flow
- Default local models: `qwen3:8b` for extraction/answers and `nomic-embed-text` for embeddings

## Run With Docker Compose

Prerequisite on Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker "$USER"
newgrp docker
docker --version
docker compose version
```

Start Postgres with pgvector, the FastAPI backend, and the Vite frontend:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Open:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000

The dev database uses:

```text
postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain
```

The compose stack uses `pgvector/pgvector:pg16` and runs `CREATE EXTENSION IF NOT EXISTS vector;` on first database initialization.

If you are using a host-managed Postgres instead of Docker, install pgvector for your Postgres version and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Useful pgvector checks:

```bash
docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If an old database volume already exists from before the init script was added, either run the `CREATE EXTENSION` command above or reset the dev database with:

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```

## Run Without Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

This expects `DATABASE_URL` to point at a running Postgres database.

## Database Migrations

Alembic owns schema creation and upgrades. The backend no longer creates tables at FastAPI startup.

Common commands:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe change"
```

The Docker backend runs migrations automatically before starting:

```text
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Ollama:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Copy `.env.example` to `.env` if you want to override defaults.
