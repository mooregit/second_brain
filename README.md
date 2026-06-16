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

   Ollama runs on the host at `http://localhost:11434`. In Docker Compose, the backend reaches that host service through `http://host.docker.internal:11434`.

   On Linux, if the backend reports `Ollama extraction failed: All connection attempts failed`, configure Ollama to listen on all interfaces for Docker:

   ```bash
   sudo systemctl edit ollama
   ```

   Add:

   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

   Then restart Ollama:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

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
   WEB_PORT=80
   PUBLIC_API_BASE_URL=http://secondbrain/api
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

5. Add the local hostname.

   ```bash
   ./scripts/setup-local-hostname.sh
   ```

   This adds the following line to `/etc/hosts`:

   ```text
   127.0.0.1 secondbrain
   ```

6. Start the full app.

   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```

7. Open the app.

   - App: http://secondbrain
   - Frontend direct port: http://localhost:5174
   - Backend health: http://localhost:8001/health
   - Backend through proxy: http://secondbrain/health

8. Verify database setup.

   ```bash
   docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
   docker compose -f docker-compose.dev.yml exec backend alembic current
   ```

9. Verify Ollama connectivity from Docker.

   ```bash
   ./scripts/check-ollama-docker.sh
   ```

   If the script says Docker Compose is not accessible, refresh Docker group membership:

   ```bash
   newgrp docker
   ```

   If needed, add your user to the Docker group and log out/in:

   ```bash
   sudo usermod -aG docker "$USER"
   ```

If ports are already in use, override them:

```bash
BACKEND_PORT=8002 FRONTEND_PORT=5175 WEB_PORT=8080 docker compose -f docker-compose.dev.yml up --build
```

If `WEB_PORT` is not `80`, open `http://secondbrain:<WEB_PORT>`.

## Platform Notes

### macOS

Install prerequisites:

- Install Docker Desktop for Mac and make sure it is running.
- Install Git if it is not already available.
- Install Ollama for macOS and start it.

Pull the local models:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Clone and start the app:

```bash
git clone https://github.com/mooregit/second_brain.git
cd second_brain
cp .env.example .env
./scripts/setup-local-hostname.sh
docker compose -f docker-compose.dev.yml up --build
```

The hostname script appends `127.0.0.1 secondbrain` to `/etc/hosts` and will ask for your macOS password through `sudo`.

Open:

- App: http://secondbrain
- Backend health: http://secondbrain/health

### Windows

Install prerequisites:

- Install Docker Desktop for Windows and make sure it is running.
- Enable WSL 2 when Docker Desktop prompts for it.
- Install Git for Windows.
- Install Ollama for Windows and start it.

Pull the local models in PowerShell:

```powershell
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Clone and start the app from PowerShell:

```powershell
git clone https://github.com/mooregit/second_brain.git
cd second_brain
copy .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

Add the local hostname by opening PowerShell as Administrator and running:

```powershell
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "127.0.0.1 secondbrain"
```

Open:

- App: http://secondbrain
- Backend health: http://secondbrain/health

If port `80` is already used on Windows, start with another web port:

```powershell
$env:WEB_PORT=8080
docker compose -f docker-compose.dev.yml up --build
```

Then open `http://secondbrain:8080`.

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

- App: http://secondbrain
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

The nginx web proxy listens on port `80` by default and maps `http://secondbrain` to the frontend, with `/api/*` routed to the backend. If port `80` is already in use, override it:

```bash
WEB_PORT=8080 docker compose -f docker-compose.dev.yml up --build
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

## Gmail Import

Gmail import is manual-first and label/query scoped. The recommended Gmail filter applies a `SecondBrain` label, then the app syncs only messages matching:

```text
label:SecondBrain
```

Local OAuth files live under `data/gmail/` and are ignored by git:

```text
data/gmail/credentials.json
data/gmail/token.json
```

Create OAuth desktop credentials in Google Cloud, download the JSON file, and save it as `data/gmail/credentials.json`. The first sync starts a local OAuth flow and writes `token.json`.

In Docker, the backend cannot open a browser. It prints an authorization URL in the backend logs. Open that URL on the host machine, approve access, and Google will redirect to:

```text
http://localhost:8090/
```

The compose stack exposes this callback port by default:

```text
8090:8090
```

Relevant settings can be edited in the app Settings page:

- Gmail enabled
- Gmail label
- Gmail query
- Auto-process imported emails

Manual sync is available from the Inbox page with `Sync Gmail`, or through the API:

```bash
curl -X POST http://secondbrain/api/gmail/sync \
  -H "Content-Type: application/json" \
  -d '{"max_results": 10}'
```

Imported messages are stored as `RawItem` records with `source_type="gmail"` and linked `EmailMessage` metadata. Duplicate Gmail message IDs are skipped. Imported emails can auto-process through the same extraction pipeline; generated replies are still draft-only and deferred.

## Troubleshooting

### Ollama Connection From Docker

The backend container reaches host Ollama at:

```text
http://host.docker.internal:11434
```

On Linux, Compose maps that hostname with:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Check host Ollama:

```bash
curl http://localhost:11434/api/tags
```

Check from inside the backend container:

```bash
docker compose -f docker-compose.dev.yml exec -T backend python - <<'PY'
import httpx
print(httpx.get("http://host.docker.internal:11434/api/tags", timeout=5).json())
PY
```

The helper script checks both host and backend-container access and warns if the configured models are missing:

```bash
./scripts/check-ollama-docker.sh
```

If it reports missing models, pull them:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Or set `OLLAMA_EXTRACTION_MODEL` in `.env` to one you already have, such as:

```env
OLLAMA_EXTRACTION_MODEL=qwen3:14b
```

If the host check fails, start Ollama and pull the models:

```bash
ollama serve
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

If the host check works but the backend-container check fails with `All connection attempts failed`, Ollama is probably bound to `127.0.0.1` only. On Linux with a systemd-managed Ollama install, run:

```bash
sudo systemctl edit ollama
```

Add:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Then restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Verify:

```bash
./scripts/check-ollama-docker.sh
```

### Ports Currently In Use

Linux/macOS:

```bash
sudo lsof -iTCP -sTCP:LISTEN -P -n
sudo lsof -i :80
sudo lsof -i :8001
sudo lsof -i :5174
```

Windows PowerShell:

```powershell
Get-NetTCPConnection -State Listen | Sort-Object LocalPort | Format-Table LocalAddress,LocalPort,OwningProcess
Get-Process -Id <PID>
```

### Docker Container View

```bash
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f frontend
docker compose -f docker-compose.dev.yml logs -f db
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build
```

Useful one-off checks:

```bash
docker compose -f docker-compose.dev.yml exec backend alembic current
docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dt"
docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
```

## Run Without Docker

Start or provide a PostgreSQL database, then set:

```bash
export DATABASE_URL=postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain
export OLLAMA_BASE_URL=http://localhost:11434
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
