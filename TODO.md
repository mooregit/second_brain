# TODO

## Phase 1: Manual Note Vertical Slice

- [x] Create FastAPI app, SQLite connection, and initial models.
- [x] Switch dev database target to Postgres.
- [x] Add Docker Compose dev stack for Postgres, backend, and frontend.
- [x] Add pgvector extension initialization for Docker Postgres.
- [x] Initialize this project as a git repository.
- [x] Add Alembic environment and initial schema migration.
- [x] Run backend migrations before Uvicorn in Docker Compose.
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
- [x] Add `Person` upsert from extraction output.
- [x] Add explicit extraction test fixture for the BetRight note.

## Phase 3: Review UI

- [x] Add Item Detail page.
- [x] Show raw source and extracted memory.
- [x] Allow editing memory summary and tags.
- [x] Add `PATCH /memories/{id}`.
- [x] Add task patch endpoint.
- [x] Add open question patch endpoint.
- [x] Add editable task fields in `ExtractionReview`.
- [x] Add editable idea fields in `ExtractionReview`.
- [x] Add editable open question fields in `ExtractionReview`.
- [ ] Add source links for every extracted child record in review UI.
- [ ] Add edit/delete/archive controls for memories, projects, tasks, ideas, decisions, and questions from their native pages.
- [ ] Add project reassignment controls for tasks, ideas, decisions, and questions outside the graph drawer.

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
- [x] Add graph filters for node type.
- [ ] Add graph filters for relationship type.
- [x] Improve graph layout so projects, work items, tags, and extracted entities are visually grouped.
- [ ] Make graph node clicks open source/detail pages.
- [x] Add a graph node detail drawer with type, source item, summary/body, project, status, tags, and edit controls.
- [x] Add graph search that can find and focus a node by label.
- [x] Highlight selected node neighbors and dim unrelated graph nodes.
- [ ] Add graph layout modes for project map, source map, task map, and entity map.
- [ ] Show edge labels on hover or selected-node focus instead of always relying on full graph labels.
- [ ] Add clearer node type styling with restrained colors/icons for projects, tasks, questions, ideas, decisions, tags, sources, and entities.
- [ ] Add graph cleanup tools for merging duplicate nodes, renaming tags/entities, reassigning records to projects, and archiving/deleting from the graph.
- [ ] Add a source trace toggle so source email/note/file nodes can be shown for audit mode and hidden for daily use.

## Phase 6: File And Folder Inputs

- [x] Add basic `POST /items/upload` for UTF-8 text.
- [ ] Store uploaded files in `data/uploads`.
- [ ] Create `FileAsset` rows with source path and metadata.
- [ ] Support `.txt` and `.md` upload acceptance tests.
- [ ] Add folder watcher for `data/inbox`.
- [ ] Convert dropped `.txt` or `.md` inbox files into raw items.
- [ ] Add a "Ways to bring in data" section near the Inbox with supported and planned import paths.
- [ ] Document Apple Notes/iCloud Notes import as an export-to-folder workflow using `.txt`, `.md`, or `.html` files.
- [ ] Add a future macOS Shortcut/AppleScript recipe for exporting Apple Notes into the watched inbox folder.
- [ ] Add Share-to-email guidance for sending Apple Notes into the Gmail SecondBrain label/inbox flow.

## Phase 7: Gmail

- [x] Add deferred Gmail endpoint stubs.
- [x] Add local OAuth setup.
- [x] Add Gmail sync implementation.
- [x] Import labeled or prefixed emails into `RawItem` and `EmailMessage`.
- [ ] Show active Gmail query on the Inbox Gmail card.
- [ ] Persist and show the latest Gmail sync result.
- [ ] Add a `Sync without auto-process` action for Gmail testing.
- [ ] Add a clearer Gmail setup/status indicator in Settings.
- [ ] Add Ollama model selection in Settings for extraction/Ask and embedding models.
- [ ] Add backend endpoint to list installed Ollama models and identify completion vs embedding-capable models.
- [ ] Add model recommendation copy in Settings for default, faster, and higher-quality local model choices.
- [ ] Add optional background Gmail polling when Gmail is enabled.
- [ ] Add Gmail draft creation implementation.
- [ ] Log every draft creation in `audit_logs`.

## Phase 8: Gmail Video Attachments

- [x] Detect Gmail video attachments during sync and store them as `FileAsset` records.
- [x] Detect Google Drive video links in Gmail messages and download them as `FileAsset` records.
- [x] Add a video ingest flow behind Gmail sync: email with a subject and attached video becomes a `RawItem` plus attachment metadata.
- [x] Add video attachment manifest text to imported Gmail `RawItem` body text.
- [x] Extract audio from video `FileAsset` records with `ffmpeg`.
- [x] Support transcript generation through `faster-whisper`.
- [x] Keep configurable `MEDIA_TRANSCRIPTION_COMMAND` as a transcription fallback.
- [x] Sample a representative video frame with `ffmpeg`.
- [x] Merge media artifact context, transcript text, and email body into the extraction prompt.
- [x] Pick and document the default local transcription backend/model.
- [ ] Pass sampled frames through a local vision model for visual context.
- [ ] Add generated frame summaries to the extraction prompt.
- [x] Add tests for Gmail video attachment import and storage.
- [x] Add tests for downstream media artifact generation and prompt enrichment.

## Product Polish Backlog

- [ ] Add a connector dashboard on the Inbox page with Manual Note, Upload File, Scan Folder, Sync Gmail, Apple Notes export, and planned connector tiles.
- [ ] Show last sync result, last error, setup status, and next action for each connector.
- [ ] Add a processing queue with `pending`, `processing`, `processed`, and `failed` states.
- [ ] Move long-running processing for Gmail/video/folder imports behind the processing queue.
- [ ] Add retry, cancel, and reprocess actions for failed or stale processing jobs.
- [ ] Improve extraction diagnostics with prompt input/context, transcript context, raw model output, repaired output, validation errors, and parsed JSON.
- [ ] Add "reprocess with edited context" from item detail.
- [ ] Add duplicate detection for projects, tags, people, URLs, and entities.
- [ ] Add merge UI for duplicate projects, tags, people, URLs, and entities.
- [ ] Add stronger project detail pages with timeline, source notes/emails/files, open tasks, questions, decisions, ideas, and a related graph slice.
- [ ] Add a Settings/import setup wizard that detects Ollama models, Gmail credentials/token status, connector health, and missing setup steps.

## Ask Improvements

- [ ] Show retrieved context before or alongside the Ask answer.
- [ ] Add Ask filters for project, source type, tag, and date range.
- [ ] Let Ask create follow-up tasks, open questions, decisions, or notes from an answer.
- [ ] Let useful Ask answers be saved as memories or decisions.
- [ ] Add Ask answer feedback so bad retrieval/extraction examples can be diagnosed later.

## Connector And Import Backlog

- [ ] Add a generic connector model/service so every integration creates `RawItem`, optional `FileAsset`, and source metadata before processing.
- [ ] Add Markdown folder import for Obsidian, Logseq, and plain `.md` note folders.
- [ ] Add local file import support for `.txt`, `.md`, `.html`, `.csv`, and `.json`.
- [ ] Add Google Drive import for docs, files, videos, and watched folders.
- [ ] Add browser bookmark/read-later imports from Chrome bookmarks, Pocket, Instapaper, and Raindrop exports.
- [ ] Add Notion import through the official Notion API for selected pages and databases.
- [ ] Add Google Calendar import for meetings, events, descriptions, and attendees.
- [ ] Add Google Docs import for project notes, specs, and meeting docs.
- [ ] Add Slack export/API import for selected channels and project conversations.
- [ ] Add Discord export/API import for selected servers/channels.
- [ ] Add GitHub import for issues, pull requests, comments, project boards, and commits.
- [ ] Add Linear import for issues, projects, comments, and statuses.
- [ ] Add Jira import for issues, projects, comments, and statuses.
- [ ] Add Trello import for boards, cards, lists, comments, and labels.
- [ ] Add RSS feed import for articles, blogs, changelogs, and release notes.
- [ ] Add Readwise/Reader import for highlights, saved articles, and notes.
- [ ] Add Kindle highlights import.
- [ ] Add YouTube transcript import from video URLs.
- [ ] Add podcast transcript import from audio files or transcript URLs.
- [ ] Add meeting transcript import for Zoom, Google Meet, Otter, Fireflies, Granola, and similar exports.
- [ ] Add PDF and ebook import with text extraction first, OCR later.
- [ ] Add Google Sheets import for selected spreadsheets and CSV-like tables.
- [ ] Add Excel import for `.xlsx` and `.csv` files.
- [ ] Add Airtable import for selected bases and tables.
- [ ] Add CRM export import for contacts, notes, tasks, and opportunities.
- [ ] Add Stripe export import for payments, customers, subscriptions, and business events.
- [ ] Add banking export import for CSV transaction files.
- [ ] Add support inbox import for support emails, tickets, and customer conversations.
- [ ] Add website analytics export import for traffic, conversions, and reporting snapshots.

## Agent Context Integrations

- [ ] Add backend endpoints for project context lookup, semantic search, and creating notes/tasks/decisions from external tools.
- [ ] Add a local `secondbrain` CLI for `search`, `ask`, `project`, `add-note`, `add-task`, and `add-decision`.
- [ ] Add a Codex skill that teaches Codex when and how to query Second Brain for project context before coding.
- [ ] Add Codex skill workflows for pulling related decisions, tasks, open questions, and source notes.
- [ ] Add Codex skill workflows for saving implementation decisions and follow-up tasks back to Second Brain.
- [ ] Add an MCP server exposing tools like `secondbrain_search`, `secondbrain_ask`, `secondbrain_get_project_context`, `secondbrain_create_note`, `secondbrain_create_task`, and `secondbrain_record_decision`.
- [ ] Add support for repo-local `.secondbrain.yml` files that map code repos to Second Brain projects, tags, and search scopes.
- [ ] Add CLI/MCP authentication or local allowlist controls before exposing write actions.
- [ ] Add README documentation for using Second Brain as context memory for Codex and other local CLI agents.

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
