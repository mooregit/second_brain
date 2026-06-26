# Second Brain Inbox

Second Brain Inbox is a local-first AI inbox for turning messy personal knowledge into structured memory.

It ingests notes, emails, files, and videos; extracts projects, tasks, ideas, decisions, questions, tags, entities, and relationships; keeps source traceability; and lets you review, search, ask, and explore that memory through a graph.

The app is designed as a working local tool, not a hosted SaaS product. When the app opens, it should go directly to the Inbox/Dashboard workflow rather than a marketing landing page. This README is the GitHub-facing product overview.

## Why It Exists

Most useful context starts messy:

- a quick note pasted into an inbox
- an email with a project request
- a video or file someone sends you
- a half-formed idea, task, decision, or open question

Second Brain Inbox turns those inputs into structured records that can be corrected, linked back to their source, searched semantically, queried through Ask, and visualized as a graph.

## What It Can Do Today

- Manual note capture.
- Gmail sync for labeled/query-matched emails.
- Google Drive video-link download from Gmail messages.
- Video audio extraction, local transcription, and media artifact storage.
- Local LLM extraction through Ollama.
- JSON validation and repair for model output.
- Editable memories, tasks, ideas, decisions, open questions, and projects.
- Postgres persistence with Alembic migrations.
- pgvector-ready database stack.
- Semantic Ask interface grounded in stored memory.
- React Flow graph with search, node detail drawer, source links, and neighbor highlighting.
- Docker Compose dev stack for Postgres, backend, frontend, and nginx.

## Local-First Principles

- Data is stored locally in Postgres and the `data/` directory.
- LLM and embedding calls default to local Ollama models.
- Gmail integration imports and processes messages locally.
- No email is auto-sent.
- Source traceability is preserved from extracted records back to raw items.
- The app favors review and correction over blindly trusting extraction.

## Screenshots

Screenshots should live under `assets/screenshots/` when added:

- Inbox and connector dashboard
- Item detail and extraction review
- Ask interface
- Graph view
- Project detail page

## Quick Start

The normal local setup is:

```bash
git clone https://github.com/mooregit/second_brain.git
cd second_brain
cp .env.example .env
ollama pull qwen3:8b
ollama pull nomic-embed-text
docker compose -f docker-compose.dev.yml up --build
```

Then open:

- App: http://secondbrain
- Backend health: http://secondbrain/health

See [Install And Run By Platform](#install-and-run-by-platform) for Linux, macOS, and Windows details.

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, Ollama HTTP API
- Frontend: React, Vite, Tailwind, React Flow
- Dev runtime: Docker Compose with Postgres + pgvector, backend, and frontend services
- Default local models: `qwen3:8b` for extraction/answers and `nomic-embed-text` for embeddings

## Ollama Models

Second Brain Inbox defaults to local Ollama models for extraction, answers, and embeddings.

Install Ollama from the official site:

- https://ollama.com/download

Default models:

- `qwen3:8b`: extraction, summarization, repair, and Ask responses.
- `nomic-embed-text`: embeddings for semantic search.

Pull the default models:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Optional fallback or larger local models:

```bash
ollama pull llama3.1:8b
ollama pull qwen3:14b
```

Model recommendations:

- Start with `qwen3:8b` for extraction and Ask. It is a good default balance of quality and local runtime.
- Use `llama3.1:8b` as a fallback if `qwen3:8b` is unavailable or behaves poorly for a specific workload.
- Use `qwen3:14b` if your machine has enough RAM/VRAM and you want better reasoning/extraction quality at the cost of speed.
- Keep `nomic-embed-text` for embeddings unless you intentionally migrate embedding storage and retrieval to a different embedding model.
- For video transcription, start with `MEDIA_TRANSCRIPTION_MODEL=base`; use a larger Whisper model later if transcript quality is more important than speed.

The app reads model settings from `.env`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EXTRACTION_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

When running with Docker Compose, Ollama runs on the host machine and the backend container reaches it through:

```text
http://host.docker.internal:11434
```

On Linux, Docker may need Ollama to listen beyond `127.0.0.1`. If extraction fails with `All connection attempts failed`, run:

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

Verify model availability:

```bash
ollama list
./scripts/check-ollama-docker.sh
```

## Project Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Roadmap](docs/ROADMAP.md)

## Install And Run By Platform

The recommended local setup is Docker Compose for the app/database plus Ollama running on the host machine. Docker starts Postgres, applies Alembic migrations, starts the FastAPI backend, starts the Vite frontend, and exposes the app through nginx at `http://secondbrain`.

### Linux

1. Install Git, Docker, Docker Compose, and curl.

   Ubuntu/Debian:

   ```bash
   sudo apt-get update
   sudo apt-get install -y git docker.io docker-compose-v2 curl
   sudo usermod -aG docker "$USER"
   newgrp docker
   docker --version
   docker compose version
   ```

   If Docker permission changes do not apply immediately, log out and back in or run `newgrp docker`.

2. Install Ollama, then pull the local models.

   Install Ollama from https://ollama.com/download or use the official Linux installer, then run:

   ```bash
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```

3. Allow Docker containers to reach host Ollama.

   If Ollama is managed by systemd:

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

4. Clone and configure the app.

   ```bash
   git clone https://github.com/mooregit/second_brain.git
   cd second_brain
   cp .env.example .env
   ./scripts/setup-local-hostname.sh
   ```

5. Start the app.

   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```

6. Open:

   - App: http://secondbrain
   - Backend health: http://secondbrain/health
   - Frontend direct port: http://localhost:5174
   - Backend direct port: http://localhost:8001/health

7. Verify the install.

   ```bash
   docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
   docker compose -f docker-compose.dev.yml exec backend alembic current
   ./scripts/check-ollama-docker.sh
   ```

### macOS

1. Install prerequisites.

   - Install Docker Desktop for Mac and start it.
   - Install Ollama for macOS and start it.
   - Install Git. If you use Homebrew:

   ```bash
   brew install git
   ```

2. Pull the local models.

   ```bash
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```

3. Clone and configure the app.

   ```bash
   git clone https://github.com/mooregit/second_brain.git
   cd second_brain
   cp .env.example .env
   ./scripts/setup-local-hostname.sh
   ```

   The hostname script adds this entry to `/etc/hosts` and will ask for your password:

   ```text
   127.0.0.1 secondbrain
   ```

4. Start the app.

   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```

5. Open:

   - App: http://secondbrain
   - Backend health: http://secondbrain/health

6. Verify the install.

   ```bash
   docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
   docker compose -f docker-compose.dev.yml exec backend alembic current
   ./scripts/check-ollama-docker.sh
   ```

### Windows

Windows is easiest with Docker Desktop using the WSL 2 backend.

1. Install prerequisites.

   - Install Docker Desktop for Windows.
   - Enable WSL 2 when Docker Desktop prompts for it.
   - Install Git for Windows.
   - Install Ollama for Windows and start it.

2. Pull the local models in PowerShell.

   ```powershell
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```

3. Clone and configure the app in PowerShell.

   ```powershell
   git clone https://github.com/mooregit/second_brain.git
   cd second_brain
   copy .env.example .env
   ```

4. Add the local hostname.

   Open PowerShell as Administrator and run:

   ```powershell
   Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "127.0.0.1 secondbrain"
   ```

5. Start the app.

   ```powershell
   docker compose -f docker-compose.dev.yml up --build
   ```

6. Open:

   - App: http://secondbrain
   - Backend health: http://secondbrain/health

7. Verify the install.

   In PowerShell:

   ```powershell
   docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\dx vector"
   docker compose -f docker-compose.dev.yml exec backend alembic current
   curl http://localhost:11434/api/tags
   ```

   The `scripts/check-ollama-docker.sh` helper is easiest from Git Bash or WSL.

If port `80` is already in use on any platform, start with another web port:

Linux/macOS:

```bash
WEB_PORT=8080 docker compose -f docker-compose.dev.yml up --build
```

Windows PowerShell:

```powershell
$env:WEB_PORT=8080
docker compose -f docker-compose.dev.yml up --build
```

Then open `http://secondbrain:8080`.

## Docker, Database, And Migrations

Start Postgres with pgvector, apply Alembic migrations, then start the FastAPI backend, Vite frontend, and nginx proxy:

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

Alembic owns schema creation and upgrades. The backend does not create tables at FastAPI startup.

Common migration commands:

```bash
docker compose -f docker-compose.dev.yml exec backend alembic current
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "describe change"
docker compose -f docker-compose.dev.yml exec backend alembic downgrade -1
```

Migration files live in:

```text
backend/migrations/
```

## File And PDF Inputs

The Inbox page supports manual notes, file uploads, and manual inbox-folder scans.

Supported upload and folder-scan formats:

- `.txt`
- `.md`
- `.pdf` files that contain selectable text

Uploaded files are copied under `data/uploads/` and linked as `FileAsset` records. PDF uploads keep the original PDF and store extracted text in the `RawItem` so the normal processing pipeline can extract memories, tasks, ideas, decisions, open questions, tags, and graph relationships.

PDF uploads return after the original file is stored, then text extraction and chunking run in the background. The parent Inbox item is marked `extracting` while text is pulled from the PDF. When chunking succeeds, the parent is marked `chunked` and page-aware `pdf_chunk` source records are queued for extraction with page start/end metadata. Chunk records are hidden from the normal Inbox list but remain available to extraction, embeddings, Ask, and graph/source tracing.

Docker Compose includes a `worker` service that drains queued extraction runs. Keep the worker running for PDF chunks, Gmail imports, GitHub/GitLab imports, and other queued processing to finish. The worker processes one queued run at a time by default to avoid overloading the local Ollama model.

The default max upload size is 100 MB. This is enforced in two places:

- nginx: `client_max_body_size 100m` in `docker/nginx/default.conf`
- backend: `MAX_UPLOAD_BYTES=104857600`

If you raise the limit, keep both values aligned and rebuild/restart the containers. A browser `413 Request Entity Too Large` response means nginx rejected the upload before the backend received it.

Scanned/image-only PDFs are not OCRed yet. For those, export or OCR the PDF to selectable text first, then upload or drop it into the inbox folder.

### Folder Inbox

The folder inbox imports supported files from the configured inbox folder. The default path is:

```text
data/inbox/
```

The path can be changed in `Settings` with the `Inbox folder` field. From the Inbox page, click `Scan inbox folder` to import new `.txt`, `.md`, or selectable-text `.pdf` files. Files are skipped after the first import by matching their source path.

For local polling or future scheduled workers, the backend includes a `FolderWatcher` service that runs the same scan behavior repeatedly.

### Apple Notes And iCloud Notes

Apple Notes does not provide a simple local API for direct ingestion, so the current supported path is export-to-folder or share-to-email:

1. Export or copy selected Apple Notes as `.txt`, `.md`, or `.html`.
2. Save the exported files into the configured inbox folder.
3. Use `Scan inbox folder` from the Inbox page.

For notes you want to route through Gmail, share or forward the note to the Gmail account connected to Second Brain and apply the configured Gmail label or query match.

Future macOS automation can use a Shortcut or AppleScript flow:

1. Select notes in Apple Notes.
2. Export note title and body as `.md` or `.txt`.
3. Save each note into the configured inbox folder.
4. Optionally run the folder scan endpoint after export.

## Gmail Import

Gmail import is manual-first and label/query scoped. The recommended Gmail filter applies a `SecondBrain` label, then the app syncs only messages matching:

```text
label:SecondBrain
```

### Gmail Connector Setup

This is the setup flow that worked for the local Docker stack.

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Select an existing project or create a new one.
3. Enable the Gmail API for that project.
4. Enable the Google Drive API for that project.
5. Open the OAuth consent screen and finish the basic app info.
6. Add these OAuth scopes under data access:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/drive.readonly`
7. Add your Gmail account under `Test users`.
   - If Google says `Ineligible accounts not added`, the address is either not a Google Account or it was entered into the wrong project.
   - Use the exact Google account you plan to sign in with.
8. Create an OAuth client.
   - Application type: `Desktop app`
   - Download the JSON file Google gives you.
9. Save that JSON file at `data/gmail/credentials.json`.
10. Make sure the local token file can be written on first login:
   - `data/gmail/token.json` will be created automatically after authorization.
11. Start the app with Docker Compose.
12. From the Inbox page, click `Sync Gmail`.
13. The backend will print an authorization URL in the container logs.
14. Open that URL in your browser on the host machine, approve access, and let Google redirect to:

```text
http://localhost:8090/
```

The backend does not try to launch a browser from inside Docker.
That is intentional, because the container usually does not have a GUI browser available.

Local OAuth files live under `data/gmail/` and are ignored by git:

```text
data/gmail/credentials.json
data/gmail/token.json
```

The compose stack exposes this callback port by default:

```text
8090:8090
```

If you need to change the callback port, update `GMAIL_OAUTH_PORT` in `.env` and expose the same port in `docker-compose.dev.yml`.

Relevant settings can be edited in the app Settings page:

- Gmail enabled
- Gmail label
- Gmail query
- Auto-process imported emails
- Gmail credentials path
- Gmail token path
- Gmail OAuth port

Manual sync is available from the Inbox page with `Sync Gmail`, or through the API:

```bash
curl -X POST http://secondbrain/api/gmail/sync \
  -H "Content-Type: application/json" \
  -d '{"max_results": 10}'
```

Imported messages are stored as `RawItem` records with `source_type="gmail"` and linked `EmailMessage` metadata. Duplicate Gmail message IDs are skipped. Imported emails can auto-process through the same extraction pipeline; generated replies are still draft-only and deferred.

### Gmail Video Attachments

When Gmail sync imports an email with `video/*` attachments, the backend stores the original video under `data/uploads/gmail/` and creates a `FileAsset` row. Processing the item runs media analysis before extraction:

- `ffmpeg` extracts a WAV audio artifact.
- `ffmpeg` samples a representative video frame.
- By default, `faster-whisper` transcribes the extracted audio locally.
- If `MEDIA_TRANSCRIPTION_BACKEND=command`, the backend runs `MEDIA_TRANSCRIPTION_COMMAND` and stores stdout or a generated `.txt` file as the transcript.
- If `MEDIA_VISION_MODEL` is set to a local Ollama vision model, the backend summarizes the sampled frame and stores it as a `frame_summary` artifact.
- The email body, attachment names, transcript, frame summary, and media artifact status are included in the extraction prompt.

If the Gmail message contains a Google Drive video link like `https://drive.google.com/file/d/...`, sync uses the Drive API to download that video into `data/uploads/drive/` and then follows the same media analysis path.

If you added Drive access after already authorizing Gmail, delete `data/gmail/token.json` and run `Sync Gmail` again so Google grants the new Drive readonly scope.

Generated media artifacts are stored under:

```text
data/media/
```

The backend Docker image includes `ffmpeg`, `libgomp1`, and the Python `faster-whisper` package. The default transcription settings are CPU-friendly:

```env
MEDIA_ARTIFACTS_FOLDER=../data/media
MEDIA_TRANSCRIPTION_BACKEND=faster-whisper
MEDIA_TRANSCRIPTION_MODEL=base
MEDIA_TRANSCRIPTION_DEVICE=cpu
MEDIA_TRANSCRIPTION_COMPUTE_TYPE=int8
MEDIA_VISION_MODEL=
```

The first transcription run may download model files inside the backend container.

Frame summaries are opt-in because they require a local vision-capable Ollama model. To enable them, pull a vision model on the host and set `MEDIA_VISION_MODEL`:

```bash
ollama pull llava:latest
```

```env
MEDIA_VISION_MODEL=llava:latest
```

If `MEDIA_VISION_MODEL` is blank, the app still stores sampled frame paths and marks the frame summary as pending.

Command-based transcription is still available as an escape hatch. Set `MEDIA_TRANSCRIPTION_BACKEND=command`, then provide a command. The command can use these placeholders:

```text
{audio_path}
{video_path}
{output_dir}
```

Example `.env` shape:

```env
MEDIA_ARTIFACTS_FOLDER=../data/media
MEDIA_TRANSCRIPTION_BACKEND=command
MEDIA_TRANSCRIPTION_COMMAND=whisper {audio_path} --model base --output_format txt --output_dir {output_dir}
```

`MEDIA_TRANSCRIPTION_COMMAND` runs inside the backend container. If the command uses `whisper` or another local transcription tool, that tool must be installed in the backend image or otherwise available inside the container.

For now, the app keeps original videos after processing so source traceability and future reprocessing are preserved.

### Gmail Troubleshooting

- If sync fails with `could not locate runnable browser`, retry after updating to the current Docker-backed flow. The backend should print the OAuth URL instead of trying to open a browser itself.
- If sync fails with `All connection attempts failed`, check that the host Ollama setup is unrelated and that the Gmail OAuth callback port is exposed in Compose.
- If Google rejects the login as a test user, go back to the OAuth consent screen and add the account under `Test users`.
- If the callback port is busy, set a different `GMAIL_OAUTH_PORT`, update the Compose port mapping, and restart the stack.

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

## Advanced: Run Without Docker

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

For non-Docker Alembic work from `backend/`:

```bash
alembic current
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
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
