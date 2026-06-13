# Architecture

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Pydantic, Ollama HTTP API.
- Frontend: React, Vite, Tailwind, React Router, React Flow.
- Local LLM: `qwen3:8b` by default, with `llama3.1:8b` as a fallback candidate.
- Embeddings: `nomic-embed-text` via Ollama, with Postgres pgvector available for vector search upgrades.
- MVP input paths: manual note and text upload, with folder watcher later.
- MVP output paths: structured memories, project/task views, Ask interface, and graph view.
- Gmail: planned after core loop works; draft replies only, no auto-send.

## Folder Structure

```text
second-brain-inbox/
  README.md
  .env.example
  .gitignore
  docker-compose.yml
  backend/
    pyproject.toml
    alembic.ini
    app/
      main.py
      core/
        config.py
        database.py
        logging.py
      models/
        base.py
        raw_item.py
        memory.py
        project.py
        person.py
        task.py
        idea.py
        decision.py
        open_question.py
        tag.py
        relationship.py
        embedding.py
        email_message.py
        file_asset.py
        processing_run.py
        draft_reply.py
        audit_log.py
      schemas/
        extraction.py
        raw_item.py
        memory.py
        ask.py
        graph.py
      api/
        routes/
          items.py
          memories.py
          projects.py
          tasks.py
          decisions.py
          questions.py
          graph.py
          ask.py
          gmail.py
          processing_runs.py
          settings.py
      services/
        ollama_client.py
        extraction_service.py
        embedding_service.py
        retrieval_service.py
        ask_service.py
        graph_service.py
        file_service.py
        folder_watcher.py
        gmail_service.py
        draft_reply_service.py
      prompts/
        extraction.md
        extraction_repair.md
        ask.md
        draft_reply.md
      workers/
        simple_worker.py
      migrations/
  frontend/
    package.json
    vite.config.ts
    tailwind.config.ts
    index.html
    src/
      main.tsx
      App.tsx
      api/
        client.ts
        items.ts
        memories.ts
        ask.ts
        graph.ts
      components/
        Layout.tsx
        Nav.tsx
        SourceLink.tsx
        ExtractionReview.tsx
        GraphCanvas.tsx
      pages/
        Dashboard.tsx
        Inbox.tsx
        ItemDetail.tsx
        Memories.tsx
        Projects.tsx
        ProjectDetail.tsx
        Tasks.tsx
        Decisions.tsx
        OpenQuestions.tsx
        Graph.tsx
        Ask.tsx
        Settings.tsx
  data/
    inbox/
    uploads/
    sqlite/
    exports/
```

## Backend Architecture

Use a layered FastAPI backend:

- API routes handle request/response only.
- Services own business logic.
- SQLAlchemy models represent persistence.
- Pydantic schemas validate API payloads and LLM extraction payloads.
- Ollama access is centralized in `OllamaClient`.
- Extraction is synchronous for the first vertical slice, then moves behind a simple worker.
- All extracted entities keep `source_raw_item_id` or `memory_id` for traceability.

Processing flow:

1. `POST /items/manual` creates `RawItem`.
2. `POST /items/{id}/process` loads raw text.
3. Backend sends extraction prompt to Ollama.
4. Backend validates JSON with `ExtractionResult`.
5. On invalid JSON, backend sends repair prompt once.
6. Backend stores `ProcessingRun`.
7. Backend upserts projects/tags/people by normalized name.
8. Backend creates memory, tasks, ideas, decisions, open questions, and relationships.
9. Backend embeds memory summary and extracted child records.
10. UI fetches the item detail and extracted memory.

## Frontend Architecture

Use React Router pages with a shared layout:

- `Dashboard`: counts, recent items, open tasks, recent projects.
- `Inbox`: raw items list, manual note composer, upload button later.
- `ItemDetail`: raw source, process button, extraction review/editor.
- `Memories`: searchable memory list.
- `Projects`: project index.
- `ProjectDetail`: project timeline, tasks, ideas, decisions, questions, sources.
- `Tasks`: task board/list with status updates.
- `Decisions`: decision log.
- `OpenQuestions`: unresolved questions.
- `Graph`: React Flow graph with filters.
- `Ask`: question input, answer, source links.
- `Settings`: Ollama model names, inbox folder path, Gmail status later.

The UI should be dense and utilitarian. It should open directly to the Dashboard/Inbox workflow, not a marketing page.

## Database

Postgres is the primary database for local development and Docker Compose. The dev stack uses `pgvector/pgvector:pg16` so the `vector` extension is available.

Default local connection string:

```text
postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain
```

Inside Docker Compose, the backend connects to:

```text
postgresql+psycopg://secondbrain:secondbrain@db:5432/second_brain
```

The extension initialization file is:

```text
docker/postgres/init/01_extensions.sql
```

It runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

For a non-Docker database, install pgvector through the OS/package manager for the active Postgres version, then run the same SQL in the target database.

Useful Docker commands:

```bash
docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "\\dx vector"
docker compose -f docker-compose.dev.yml exec db psql -U secondbrain -d second_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Migrations

Alembic owns schema management.

- Migration config: `backend/alembic.ini`
- Migration environment: `backend/migrations/env.py`
- Revisions: `backend/migrations/versions/`
- SQLAlchemy metadata source: `app.core.database.Base`
- Model imports: `app.models`

The backend container runs `alembic upgrade head` before starting FastAPI. Local development should do the same before running the server against a fresh database.

Useful commands:

```bash
cd backend
source .venv/bin/activate
alembic heads
alembic current
alembic upgrade head
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

## Database Schema

Use SQLAlchemy ORM with UUID primary keys and timestamp columns.

### `raw_items`

- `id`
- `source_type`: `manual | upload | folder | gmail`
- `title`
- `body_text`
- `content_type`
- `status`: `new | processing | processed | failed | archived`
- `source_uri`
- `metadata_json`
- `created_at`
- `updated_at`

### `memories`

- `id`
- `raw_item_id`
- `memory_type`
- `summary`
- `confidence`
- `validated_json`
- `raw_llm_output`
- `created_at`
- `updated_at`

### `projects`

- `id`
- `name`
- `description`
- `created_at`
- `updated_at`

### `people`

- `id`
- `name`
- `email`
- `metadata_json`

### `tasks`

- `id`
- `memory_id`
- `project_id`
- `title`
- `description`
- `priority`
- `status`
- `due_date`
- `source_raw_item_id`

### `ideas`

- `id`
- `memory_id`
- `project_id`
- `body`
- `source_raw_item_id`

### `decisions`

- `id`
- `memory_id`
- `project_id`
- `title`
- `rationale`
- `confidence`
- `decided_at`
- `source_raw_item_id`

### `open_questions`

- `id`
- `memory_id`
- `project_id`
- `question`
- `status`: `open | answered | archived`
- `source_raw_item_id`

### `tags`

- `id`
- `name`

### `memory_tags`

- `memory_id`
- `tag_id`

### `relationships`

- `id`
- `memory_id`
- `source_label`
- `target_label`
- `relationship_type`
- `source_node_type`
- `target_node_type`
- `source_raw_item_id`

### `embeddings`

- `id`
- `owner_type`: `memory | raw_item | task | project | decision | open_question`
- `owner_id`
- `model`
- `vector_json`
- `text_hash`
- `created_at`

### `email_messages`

- `id`
- `raw_item_id`
- `gmail_message_id`
- `thread_id`
- `from_email`
- `to_email`
- `subject`
- `sent_at`
- `labels_json`
- `headers_json`

### `file_assets`

- `id`
- `raw_item_id`
- `filename`
- `stored_path`
- `mime_type`
- `size_bytes`
- `sha256`

### `processing_runs`

- `id`
- `raw_item_id`
- `status`
- `model`
- `prompt_version`
- `started_at`
- `finished_at`
- `error`
- `raw_output`
- `parsed_json`

### `draft_replies`

- `id`
- `email_message_id`
- `body`
- `status`: `draft | created_in_gmail | discarded`
- `gmail_draft_id`
- `created_at`

### `audit_logs`

- `id`
- `action`
- `entity_type`
- `entity_id`
- `metadata_json`
- `created_at`

## LLM Prompt Design

Extraction prompt rules:

- System: local memory extraction engine.
- Require strict JSON only.
- No markdown.
- No commentary.
- Preserve uncertainty.
- Do not invent deadlines, people, or projects.
- Use `null` where unknown.
- Use ISO date strings when dates are explicit or inferable from provided context.
- Include confidence from `0` to `1`.

Validated schema:

```json
{
  "summary": "string",
  "memory_type": "note | task | idea | decision | question | resource | email | file",
  "projects": ["string"],
  "people": ["string"],
  "tasks": [
    {
      "title": "string",
      "description": "string|null",
      "priority": "low|medium|high|null",
      "due_date": "string|null",
      "status": "open"
    }
  ],
  "ideas": ["string"],
  "decisions": [
    {
      "title": "string",
      "rationale": "string|null",
      "confidence": 0.0
    }
  ],
  "open_questions": ["string"],
  "tags": ["string"],
  "entities": ["string"],
  "relationships": [
    {
      "source": "string",
      "target": "string",
      "relationship": "string"
    }
  ],
  "suggested_actions": ["string"],
  "confidence": 0.0
}
```

Repair prompt:

- Include validation error.
- Include original invalid output.
- Ask model to return corrected JSON only.
- Do not re-extract from scratch unless necessary.

Ask prompt:

- Answer only from retrieved context.
- Cite source IDs/titles.
- If context is insufficient, say so directly.
- Separate answer from sources.

## Embedding And Search

Use Ollama embeddings first:

- Default model: `nomic-embed-text`.
- Store vectors in Postgres for MVP.
- Compute cosine similarity in Python for small local datasets.
- Embed memory summaries, raw item body snippets, tasks, decisions, open questions, and project descriptions.

Retrieval flow for `/ask`:

1. Embed user question.
2. Retrieve top matching embeddings by cosine similarity.
3. Load related records and source raw items.
4. Build compact context with source IDs.
5. Ask local LLM to answer only from context.
6. Return answer plus source links.

Upgrade path:

- For larger datasets, switch similarity search to native Postgres pgvector indexes.
- Keep embedding service interface stable so storage can change without touching API routes.

## Graph / Mind Map

Use React Flow.

Backend `GET /graph` returns:

```json
{
  "nodes": [
    {
      "id": "string",
      "type": "project|task|idea|decision|question|person|tag|source|entity",
      "label": "string",
      "metadata": {}
    }
  ],
  "edges": [
    {
      "id": "string",
      "source": "string",
      "target": "string",
      "label": "string",
      "relationship_type": "string"
    }
  ]
}
```

Graph behavior:

- Show projects as primary nodes.
- Connect projects to tasks, ideas, decisions, questions, people, files, emails, and tags.
- Include extracted relationships as labeled edges.
- Support filters for project, tag, source type, and date range.
- Clicking a node opens the source item or detail page.
- Duplicate merge can be a later feature with manual aliasing.

## API Endpoints

- `POST /items/manual`
- `POST /items/upload`
- `GET /items`
- `GET /items/{id}`
- `POST /items/{id}/process`
- `GET /memories`
- `GET /memories/{id}`
- `PATCH /memories/{id}`
- `GET /projects`
- `GET /projects/{id}`
- `GET /tasks`
- `PATCH /tasks/{id}`
- `GET /decisions`
- `GET /open-questions`
- `PATCH /open-questions/{id}`
- `GET /graph`
- `POST /ask`
- `POST /gmail/sync`
- `POST /gmail/draft-reply`
- `GET /processing-runs`
- `GET /settings`
- `PATCH /settings`

## Gmail Integration Plan

Add Gmail after the manual-note loop is useful.

MVP Gmail behavior:

- OAuth credentials stored locally in `.env` and local token files ignored by git.
- Poll Gmail manually through `POST /gmail/sync`.
- Later run polling every few minutes.
- Only import messages matching configured label, subject prefix, or sender rule.
- Recommended default Gmail label: `SecondBrain`.
- Recommended default subject prefix: `[SB]`.
- Store message metadata and body in `EmailMessage` plus `RawItem`.
- Process imported emails through the same extraction pipeline.
- Mark processed messages with a local DB state first.
- Later optionally apply Gmail `Processed` label.

Draft replies:

- `POST /gmail/draft-reply`.
- Generate a draft body using retrieved memory and email context.
- Create Gmail draft only.
- Never auto-send in MVP.
- Log every draft creation in `audit_logs`.
