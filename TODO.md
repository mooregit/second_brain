# TODO

## Phase 1: Manual Note Vertical Slice

- [x] Create FastAPI app, SQLite connection, and initial models.
- [x] Switch dev database target to Postgres.
- [x] Add Docker Compose dev stack for Postgres, backend, and frontend.
- [x] Add pgvector extension initialization for Docker Postgres.
- [x] Initialize this project as a git repository.
- [x] Add Alembic environment and initial schema migration.
- [x] Run backend migrations before Uvicorn in Docker Compose.
- [ ] Install Docker on host machine. Blocked in this session because `sudo` requires a password.
- [x] Add `POST /items/manual`.
- [x] Add `GET /items`.
- [x] Add `GET /items/{id}`.
- [x] Build Inbox page with note textarea and item list.
- [x] Persist pasted notes as `RawItem`.

## Phase 2: Extraction Pipeline

- [x] Add Ollama client.
- [x] Add extraction prompt.
- [x] Add repair prompt.
- [x] Add Pydantic `ExtractionResult`.
- [x] Add `POST /items/{id}/process`.
- [x] Store `ProcessingRun`, `Memory`, `Project`, `Task`, `Idea`, `OpenQuestion`, `Tag`, and `Relationship`.
- [ ] Add `Person` upsert from extraction output.
- [ ] Add explicit extraction test fixture for the BetRight note.

## Phase 3: Review UI

- [x] Add Item Detail page.
- [x] Show raw source and extracted memory.
- [x] Allow editing memory summary and tags.
- [x] Add `PATCH /memories/{id}`.
- [x] Add task patch endpoint.
- [x] Add open question patch endpoint.
- [ ] Add editable task fields in `ExtractionReview`.
- [ ] Add editable idea fields in `ExtractionReview`.
- [ ] Add editable open question fields in `ExtractionReview`.
- [ ] Add source links for every extracted child record in review UI.

## Phase 4: Ask Interface

- [x] Add embedding service using Ollama.
- [x] Store embeddings for memories and child records during processing.
- [x] Add retrieval service with cosine similarity in Python.
- [x] Add `POST /ask`.
- [x] Build Ask page with answer and source links.
- [ ] Add deterministic tests for empty-context answers.
- [ ] Add deterministic tests for retrieved-source answers.

## Phase 5: Graph View

- [x] Add graph service.
- [x] Add `GET /graph`.
- [x] Build React Flow graph.
- [x] Show projects, tasks, ideas, questions, tags, entities, and relationships.
- [ ] Add graph filters for project, tag, source type, and date range.
- [ ] Make graph node clicks open source/detail pages.

## Phase 6: File And Folder Inputs

- [x] Add basic `POST /items/upload` for UTF-8 text.
- [ ] Store uploaded files in `data/uploads`.
- [ ] Create `FileAsset` rows with source path and metadata.
- [ ] Support `.txt` and `.md` upload acceptance tests.
- [ ] Add folder watcher for `data/inbox`.
- [ ] Convert dropped `.txt` or `.md` inbox files into raw items.

## Phase 7: Gmail

- [x] Add deferred Gmail endpoint stubs.
- [ ] Add local OAuth setup.
- [ ] Add Gmail sync implementation.
- [ ] Import labeled or prefixed emails into `RawItem` and `EmailMessage`.
- [ ] Add Gmail draft creation implementation.
- [ ] Log every draft creation in `audit_logs`.

## Backend Tests

- [ ] Verify `docker compose -f docker-compose.dev.yml up --build` starts all services cleanly.
- [ ] Verify Postgres startup creates the `vector` extension.
- [ ] `POST /items/manual` creates raw item.
- [ ] Extraction schema accepts valid model JSON.
- [ ] Extraction schema rejects invalid JSON.
- [ ] Repair path stores both original and repaired output.
- [ ] Processing creates linked memory/project/task/idea/question/tag/relationship records.
- [ ] Embedding service stores vector rows.
- [ ] Ask endpoint refuses to answer without context.
- [ ] Ask endpoint returns sources when context exists.
- [ ] Graph endpoint returns nodes and edges for extracted relationships.

## Frontend Tests

- [ ] Inbox note submission renders new item.
- [ ] Process button updates item detail.
- [ ] Extraction review displays editable fields.
- [ ] Ask page shows answer and source links.
- [ ] Graph page renders nodes from API response.

## Manual Acceptance

- [ ] Process the BetRight injury note.
- [ ] Confirm project `BetRight` is created.
- [ ] Confirm task `Add injury classification for BetRight` is created.
- [ ] Confirm idea `Use local LLM to categorize ESPN injury blurbs` is created.
- [ ] Confirm open question `Should injury status directly adjust player prop projections?` is created.
- [ ] Confirm tags include `BetRight`, `injuries`, and `local-llm`.
- [ ] Confirm relationship `injury classification may_affect player prop projections` is created.
- [ ] Confirm Ask returns BetRight injury task when queried.
- [ ] Confirm Graph shows BetRight connected to extracted items.
