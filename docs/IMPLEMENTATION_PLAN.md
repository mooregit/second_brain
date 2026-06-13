# Implementation Plan

## Summary

Build a local-first second brain inbox as a standalone app at `/home/rmoore/dev/second-brain-inbox`.

The dev runtime should be started with Docker Compose using `docker-compose.dev.yml`. The stack includes Postgres with pgvector, the FastAPI backend, and the Vite frontend.

The first usable slice is:

```text
Manual note -> RawItem -> Ollama extraction -> Pydantic validation -> structured records -> UI review -> Ask -> simple graph
```

## MVP Scope

Build in v1:

- Manual note entry.
- Raw item storage.
- Local LLM extraction with strict JSON.
- One JSON repair retry on invalid output.
- Editable extracted memory review.
- SQLite persistence for raw items, memories, projects, people, tasks, ideas, decisions, open questions, tags, relationships, embeddings, and processing runs.
- Semantic search using local embeddings.
- Ask interface using retrieval augmented generation.
- Dashboard, Inbox, Item Detail, Memories, Projects, Tasks, Decisions, Open Questions, Graph, Ask, and Settings views.
- Simple graph showing projects, tasks, ideas, questions, entities, and relationships.
- Source traceability from every extracted record back to the raw item.

Defer from MVP:

- Gmail OAuth ingestion.
- Gmail draft replies.
- Attachment OCR.
- PDF parsing beyond simple uploaded text files.
- PostgreSQL migration.
- Multi-user accounts.
- Auto-send email.
- Advanced duplicate merge UX.
- Background job framework beyond simple local worker or polling.

## Phases

### Phase 1: Manual Note Vertical Slice

Tasks:

- Create FastAPI app, SQLite connection, and initial models.
- Add `POST /items/manual`, `GET /items`, and `GET /items/{id}`.
- Build Inbox page with note textarea and item list.
- Store pasted notes as `RawItem`.

Acceptance:

- User can paste a note in the UI.
- Note appears in Inbox.
- Raw item is persisted in SQLite.

### Phase 2: Extraction Pipeline

Tasks:

- Add Ollama client.
- Add extraction and repair prompts.
- Add Pydantic `ExtractionResult`.
- Add `POST /items/{id}/process`.
- Store `ProcessingRun`, `Memory`, `Project`, `Task`, `Idea`, `OpenQuestion`, `Tag`, and `Relationship`.

Acceptance:

- Example BetRight note extracts valid structured JSON.
- Invalid JSON triggers one repair attempt.
- Raw LLM output and parsed JSON are stored.

### Phase 3: Review UI

Tasks:

- Add Item Detail page.
- Show raw source and extracted memory.
- Allow editing memory summary, tags, tasks, ideas, and questions.
- Add `PATCH /memories/{id}` and task/question patch endpoints.

Acceptance:

- User can correct extracted data before relying on it.
- Every extracted item links back to raw source.

### Phase 4: Ask Interface

Tasks:

- Add embedding service using Ollama.
- Store embeddings for memories and child records.
- Add retrieval service with cosine similarity in Python.
- Add `POST /ask`.
- Build Ask page with answer and source links.

Acceptance:

- Asking "What are my open BetRight tasks?" returns stored BetRight task context.
- Answer includes source links.
- If no context exists, app says there is not enough information.

### Phase 5: Graph View

Tasks:

- Add graph service and `GET /graph`.
- Build React Flow graph.
- Show projects, tasks, ideas, questions, tags, entities, and relationships.
- Add basic filters.

Acceptance:

- BetRight note creates visible connected graph nodes.
- Clicking a node opens source or detail page.

### Phase 6: File And Folder Inputs

Tasks:

- Add `POST /items/upload`.
- Store uploaded files in `data/uploads`.
- Extract text for `.txt`, `.md`, and simple text-like files first.
- Add folder watcher for `data/inbox`.

Acceptance:

- Dropping a `.txt` or `.md` file into inbox creates a raw item.
- Uploaded file records retain source path and metadata.

### Phase 7: Gmail

Tasks:

- Add local OAuth setup.
- Add Gmail sync endpoint.
- Import labeled or prefixed emails into `RawItem` and `EmailMessage`.
- Add Gmail draft creation endpoint.

Acceptance:

- Manual Gmail sync imports `[SB]` or labeled messages.
- Imported emails process through the same pipeline.
- Reply generation creates drafts only.

## Local Commands

Initial setup:

```bash
mkdir second-brain-inbox
cd second-brain-inbox
mkdir -p backend frontend data/inbox data/uploads data/sqlite data/exports
```

Ollama models:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Docker Compose dev stack:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Open:

- Frontend: `http://localhost:5174`
- Backend: `http://localhost:8001`
- Postgres: `localhost:5432`

Backend without Docker:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install @tanstack/react-query react-router-dom reactflow lucide-react clsx
npm install -D tailwindcss postcss autoprefixer
npm run dev
```

Environment:

```env
DATABASE_URL=postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EXTRACTION_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
INBOX_FOLDER=../data/inbox
POSTGRES_DB=second_brain
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=secondbrain
```

Postgres vector extension:

- Docker Compose uses `pgvector/pgvector:pg16`, so pgvector is already installed in the database image.
- The init SQL at `docker/postgres/init/01_extensions.sql` runs `CREATE EXTENSION IF NOT EXISTS vector;` when the database volume is first created.
- For a host-managed Postgres, install the pgvector package for the local Postgres version, then run `CREATE EXTENSION IF NOT EXISTS vector;` in the `second_brain` database.
- If the Docker volume already existed before the init script was added, run `docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"`.

Alembic:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

The backend compose service runs `alembic upgrade head` before starting Uvicorn.

## Testing Plan

Backend tests:

- `POST /items/manual` creates raw item.
- Extraction schema accepts valid model JSON.
- Extraction schema rejects invalid JSON.
- Repair path stores both original and repaired output.
- Processing creates linked memory/project/task/idea/question/tag/relationship records.
- Embedding service stores vector rows.
- Ask endpoint refuses to answer without context.
- Ask endpoint returns sources when context exists.
- Graph endpoint returns nodes and edges for extracted relationships.

Frontend tests:

- Inbox note submission renders new item.
- Process button updates item detail.
- Extraction review displays editable fields.
- Ask page shows answer and source links.
- Graph page renders nodes from API response.

Manual acceptance test:

```text
Need to add injury classification to BetRight. Could use ESPN blurbs and categorize as minor, serious, questionable, out. Also need to check if this affects player prop projections. Maybe use local LLM first.
```

Expected:

- Project: `BetRight`
- Task: `Add injury classification for BetRight`
- Idea: `Use local LLM to categorize ESPN injury blurbs`
- Open question: `Should injury status directly adjust player prop projections?`
- Tags include `BetRight`, `injuries`, `local-llm`
- Relationship: `injury classification may_affect player prop projections`
- Ask returns BetRight injury task when queried.
- Graph shows BetRight connected to extracted items.
