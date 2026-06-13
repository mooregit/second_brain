# Second Brain Inbox

Local-first inbox for turning raw notes into structured memories, tasks, decisions, questions, graph nodes, and grounded answers.

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, Ollama HTTP API
- Frontend: React, Vite, Tailwind, React Flow
- Dev runtime: Docker Compose with Postgres + pgvector, backend, and frontend services
- Default local models: `qwen3:8b` for extraction/answers and `nomic-embed-text` for embeddings

## Install From Scratch

1. Install system prerequisites.

   Ubuntu:

   ```bash
   sudo apt-get update
   sudo apt-get install -y git docker.io docker-compose-v2 curl
   sudo usermod -aG docker "$USER"
   newgrp docker
   docker --version
   docker compose version
   ```

2. Install and start Ollama.

   Follow the Ollama install instructions for your OS, then pull the local models:

   ```bash
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```

   The backend expects Ollama at `http://localhost:11434` on the host. In Docker Compose, the backend reaches it through `http://host.docker.internal:11434`.

3. Clone the project.

   ```bash
   git clone git@github.com:mooregit/second_brain.git
   cd second_brain
   ```

   HTTPS clone also works:

   ```bash
   git clone https://github.com/mooregit/second_brain.git
   cd second_brain
   ```

4. Create local environment overrides if needed.

   ```bash
   cp .env.example .env
   ```

   The default Docker setup uses:

   ```env
   POSTGRES_DB=second_brain
   POSTGRES_USER=secondbrain
   POSTGRES_PASSWORD=secondbrain
   BACKEND_PORT=8001
   FRONTEND_PORT=5174
   OLLAMA_BASE_URL=http://localhost:11434
   ```

5. Start the full app.

   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```

6. Open the app.

   - Frontend: http://localhost:5174
   - Backend health: http://localhost:8001/health

7. Verify database setup.

   ```bash
   docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
   docker compose -f docker-compose.dev.yml exec backend alembic current
   ```

If ports are already in use, override them:

```bash
BACKEND_PORT=8002 FRONTEND_PORT=5175 docker compose -f docker-compose.dev.yml up --build
```

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

Start Postgres with pgvector, apply Alembic migrations, then start the FastAPI backend and Vite frontend:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Open:

- Frontend: http://localhost:5174
- Backend: http://localhost:8001

The dev database uses:

```text
postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain
```

Inside Docker, the backend connects to:

```text
postgresql+psycopg://secondbrain:secondbrain@db:5432/second_brain
```

The backend listens on port `8000` inside the container and maps to host port `8001` by default to avoid conflicts with local FastAPI servers. Override it with:

```bash
BACKEND_PORT=8002 docker compose -f docker-compose.dev.yml up --build
```

The frontend listens on port `5173` inside the container and maps to host port `5174` by default to avoid conflicts with local Vite servers. Override it with:

```bash
FRONTEND_PORT=5175 docker compose -f docker-compose.dev.yml up --build
```

The compose stack uses `pgvector/pgvector:pg16` and runs this on first database initialization:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The backend service also runs Alembic before Uvicorn:

```text
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

Start or provide a PostgreSQL database, then set:

```bash
export DATABASE_URL=postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain
```

If you are using a host-managed Postgres instead of Docker, install pgvector for your Postgres version and run this in the target database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
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

## Database Migrations

Alembic owns schema creation and upgrades. The backend no longer creates tables at FastAPI startup.

Common commands:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

Migration files live in:

```text
backend/migrations/
```

Copy `.env.example` to `.env` if you want to override defaults.
