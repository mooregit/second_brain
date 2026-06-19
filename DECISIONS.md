# Decisions

## Accepted

### Build As A Local-First Standalone App

The app lives at `/home/rmoore/dev/second-brain-inbox` and is intended for a single local user in the MVP.

Rationale:

- Keeps privacy-sensitive notes and email-derived content local.
- Avoids account, tenancy, and deployment complexity while validating the core loop.

### Use FastAPI, SQLAlchemy, PostgreSQL, And Pydantic For The Backend

Backend stack:

- FastAPI for HTTP API.
- SQLAlchemy ORM for persistence.
- PostgreSQL for MVP storage.
- Pydantic for API and LLM payload validation.

Rationale:

- Fits a local app while matching the production-grade relational database target early.
- Avoids a later SQLite-to-Postgres migration once the schema grows.
- Pydantic gives a hard validation boundary around local model output.

### Use Docker Compose For Local Dev

The dev stack runs through `docker-compose.dev.yml` with services for Postgres, backend, and frontend.

Rationale:

- One command starts the full application.
- Backend and frontend dependencies are isolated from the host.
- Postgres and pgvector setup is reproducible.

### Use Alembic For Database Schema Management

Alembic is responsible for database schema creation and upgrades. FastAPI startup does not call `Base.metadata.create_all()`.

Rationale:

- Schema changes are reviewable and repeatable.
- Docker startup can apply migrations consistently.
- Postgres environments can be upgraded without ad hoc table creation.

### Use React, Vite, Tailwind, And React Flow For The Frontend

Frontend stack:

- React and Vite for the app shell.
- Tailwind for compact utility styling.
- React Router for views.
- React Flow for the graph view.

Rationale:

- Fast local iteration.
- React Flow avoids hand-rolling graph interaction.
- The UI should be dense and workflow-oriented rather than a marketing page.

### Use Ollama For Local Generation And Embeddings

Model defaults:

- Extraction and answer model: `qwen3:8b`.
- Fallback candidate: `llama3.1:8b`.
- Embedding model: `nomic-embed-text`.

Rationale:

- Keeps extraction, search, and answer generation local.
- Supports source-sensitive personal notes without remote API dependency.

### Require Strict JSON Extraction With One Repair Retry

The extraction path requires JSON matching `ExtractionResult`. Invalid JSON gets one repair prompt that includes the validation error and original invalid output.

Rationale:

- Local 8B models can produce malformed JSON.
- One repair attempt improves usability without hiding repeated extraction failures.
- Raw and parsed outputs are stored for auditability.

### Keep Review/Edit Central

Extracted memories and child records should be reviewable and correctable before the user relies on them.

Rationale:

- Local model extraction quality varies.
- A visible review step mitigates hallucinated or poorly structured records.

### Preserve Source Traceability

Every derived record stores `memory_id` and/or `source_raw_item_id`.

Rationale:

- Ask answers and graph nodes need source links.
- Users must be able to inspect the raw note behind every extracted fact.

### Position Around Obsidian As An Ingestion Engine

Second Brain Inbox should not try to compete with Obsidian as a note editor. Obsidian is already a mature local-first workspace for writing, Markdown files, links, graph exploration, web clipping, Canvas, and plugin-driven workflows.

Decision:

- Position Second Brain Inbox as a local AI ingestion and extraction engine.
- Let it stand alone for users who want an app workflow.
- Also support exporting reviewed memory into Obsidian-friendly Markdown and graph artifacts later.

Rationale:

- The app's strongest differentiator is turning raw inputs into structured, source-traceable records.
- Obsidian is better suited for long-form writing, manual note gardening, and vault-based knowledge work.
- Interoperability is more valuable than duplicating Obsidian's editor and plugin ecosystem.

Future export direction:

- Export reviewed memories to an Obsidian vault as Markdown.
- Include frontmatter, backlinks, source links, and raw item traceability.
- Add Canvas/graph-compatible relationship data where useful.

### Use Postgres With pgvector Available For Search

Embeddings are stored in Postgres for MVP scale. The Docker database image includes pgvector and initializes the `vector` extension so native vector indexes can be added when needed.

Rationale:

- Still local and reproducible through Docker Compose.
- Good enough for small datasets.
- The embedding service boundary can later move similarity search from Python cosine to Postgres pgvector queries.

### Defer Gmail Until The Manual Note Loop Is Useful

Gmail ingestion and draft replies are planned after the core manual-note loop works.

Rationale:

- OAuth and email edge cases can slow delivery.
- Manual notes validate extraction, review, Ask, and graph behavior first.

### Never Auto-Send Email In MVP

Gmail replies, when implemented, create drafts only. Auto-send is excluded from MVP.

Rationale:

- Email automation is high-risk.
- Any future auto-send would require explicit opt-in, whitelist rules, confidence thresholds, and audit logs.

## Assumptions

- Single local user for MVP.
- PostgreSQL is the default database for the first version.
- Ollama is installed and running locally.
- Gmail is not part of the first vertical slice.
- No email is ever auto-sent in MVP.

## Risks And Mitigations

### Local Model Returns Invalid JSON

Mitigation:

- Strict prompt.
- Pydantic validation.
- One repair retry.
- Store failures visibly.

### 8B Model Extraction Quality Varies

Mitigation:

- Keep review/edit loop central.
- Allow model selection in settings.

### Python Vector Search Is Slow At Scale

Mitigation:

- Use Python cosine search for MVP.
- Keep interface ready for native Postgres `pgvector` indexes and nearest-neighbor queries.

### Gmail OAuth Slows Delivery

Mitigation:

- Defer Gmail until manual note loop proves value.

### The App Becomes Too Complex To Use

Mitigation:

- Default landing page is Inbox/Dashboard.
- Every item has one obvious Process button and one Review screen.

### Source Traceability Gets Lost

Mitigation:

- Every derived record stores `memory_id` and/or `source_raw_item_id`.

### Auto-Emailing Creates Risk

Mitigation:

- Drafts only in MVP.
- Future auto-send requires whitelist, confidence threshold, audit log, and explicit opt-in.
