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
- [x] Add source links for every extracted child record in review UI.
- [ ] Add a review action to create a new project directly from a processed memory or extracted project suggestion.
- [x] Add edit/delete/archive controls for memories, projects, tasks, ideas, decisions, and questions from their native pages.
- [x] Add project reassignment controls for tasks, ideas, decisions, and questions outside the graph drawer.

## Phase 4: Ask Interface

- [x] Add embedding service using Ollama.
- [x] Store embeddings for memories and child records during processing.
- [x] Add retrieval service with cosine similarity in Python.
- [x] Add `POST /ask`.
- [x] Build Ask page with answer and source links.
- [x] Add deterministic tests for empty-context answers.
- [x] Add deterministic tests for retrieved-source answers.

## Phase 5: Graph View

- [x] Add graph service.
- [x] Add `GET /graph`.
- [x] Build React Flow graph.
- [x] Show projects, tasks, ideas, questions, tags, entities, and relationships.
- [x] Add graph filters for project, tag, source type, and date range.
- [x] Add graph filters for node type.
- [x] Add graph filters for relationship type.
- [x] Improve graph layout so projects, work items, tags, and extracted entities are visually grouped.
- [x] Make graph node clicks open source/detail pages.
- [x] Add a graph node detail drawer with type, source item, summary/body, project, status, tags, and edit controls.
- [x] Add graph search that can find and focus a node by label.
- [x] Highlight selected node neighbors and dim unrelated graph nodes.
- [x] Add graph layout modes for project map, source map, task map, and entity map.
- [x] Add a D3 force-powered cluster map that can grow in all directions and group similar/connected topics.
- [x] Show edge labels on hover or selected-node focus instead of always relying on full graph labels.
- [x] Add clearer node type styling with restrained colors/icons for projects, tasks, questions, ideas, decisions, tags, sources, and entities.
- [x] Add graph cleanup tools for merging duplicate nodes, renaming tags/entities, reassigning records to projects, and archiving/deleting from the graph.
- [x] Add manual graph attachment controls for creating relationships between orphaned nodes/cards and projects or other nodes.
- [x] Add a source trace toggle so source email/note/file nodes can be shown for audit mode and hidden for daily use.

## Phase 6: File And Folder Inputs

- [x] Add basic `POST /items/upload` for UTF-8 text.
- [x] Store uploaded files in `data/uploads`.
- [x] Create `FileAsset` rows with source path and metadata.
- [x] Support `.txt` and `.md` upload acceptance tests.
- [x] Add folder watcher for `data/inbox`.
- [x] Convert dropped `.txt` or `.md` inbox files into raw items.
- [x] Add a "Ways to bring in data" section near the Inbox with supported and planned import paths.
- [x] Document Apple Notes/iCloud Notes import as an export-to-folder workflow using `.txt`, `.md`, or `.html` files.
- [x] Add a future macOS Shortcut/AppleScript recipe for exporting Apple Notes into the watched inbox folder.
- [x] Add Share-to-email guidance for sending Apple Notes into the Gmail SecondBrain label/inbox flow.

## Phase 7: Gmail

- [x] Add deferred Gmail endpoint stubs.
- [x] Add local OAuth setup.
- [x] Add Gmail sync implementation.
- [x] Import labeled or prefixed emails into `RawItem` and `EmailMessage`.
- [x] Show active Gmail query on the Inbox Gmail card.
- [x] Persist and show the latest Gmail sync result.
- [x] Add a `Sync without auto-process` action for Gmail testing.
- [x] Add a clearer Gmail setup/status indicator in Settings.
- [x] Add Ollama model selection in Settings for extraction/Ask and embedding models.
- [x] Add backend endpoint to list installed Ollama models and identify completion vs embedding-capable models.
- [x] Add model recommendation copy in Settings for default, faster, and higher-quality local model choices.
- [x] Add optional background Gmail polling when Gmail is enabled.
- [x] Add Gmail draft creation implementation.
- [x] Log every draft creation in `audit_logs`.

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
- [x] Pass sampled frames through a local vision model for visual context.
- [x] Add generated frame summaries to the extraction prompt.
- [x] Add tests for Gmail video attachment import and storage.
- [x] Add tests for downstream media artifact generation and prompt enrichment.

## Product Polish Backlog

- [x] Add a connector dashboard on the Inbox page with Manual Note, Upload File, Scan Folder, Sync Gmail, Apple Notes export, and planned connector tiles.
- [x] Show last sync result, last error, setup status, and next action for each connector.
- [x] Add a processing queue with `pending`, `processing`, `processed`, and `failed` states.
- [x] Move long-running processing for Gmail/video/folder imports behind the processing queue.
- [x] Add retry, cancel, and reprocess actions for failed or stale processing jobs.
- [ ] Add a reprocess failed ingestions workflow that finds failed raw items/imports, shows the connector/source error, and retries ingestion or queues extraction again.
- [ ] Improve extraction diagnostics with prompt input/context, transcript context, raw model output, repaired output, validation errors, and parsed JSON.
- [ ] Add "reprocess with edited context" from item detail.
- [ ] Fix large file upload handling for PDFs and other documents: raise nginx `client_max_body_size`, align backend upload limits, show a clear UI error for 413 responses, and document the configured max upload size.
- [ ] Add duplicate detection for projects, tags, people, URLs, and entities.
- [ ] Add merge UI for duplicate projects, tags, people, URLs, and entities.
- [ ] Add stronger project detail pages with timeline, source notes/emails/files, open tasks, questions, decisions, ideas, and a related graph slice.
- [ ] Add a Settings/import setup wizard that detects Ollama models, Gmail credentials/token status, connector health, and missing setup steps.
- [ ] Add hardware-aware Ollama model recommendations in Settings, including notes that `gpt-oss:20b` is MXFP4-quantized but still heavy/experimental on 16GB RAM and 8GB VRAM.
- [ ] Add model profiles such as fast/local-small, balanced/default, higher-quality, and experimental-heavy with recommended extraction/Ask/vision/embedding model choices.

## Ask Improvements

- [ ] Show retrieved context before or alongside the Ask answer.
- [ ] Add Ask filters for project, source type, tag, and date range.
- [ ] Let Ask create follow-up tasks, open questions, decisions, or notes from an answer.
- [ ] Let useful Ask answers be saved as memories or decisions.
- [ ] Add Ask answer feedback so bad retrieval/extraction examples can be diagnosed later.

## Action Items And Prompt Generation

- [ ] Add a first-class action item layer that can wrap or reference tasks, open questions, ideas, decisions, GitHub issues/PRs, and other work records without removing them from the knowledge base.
- [ ] Let tasks, questions, ideas, and decisions be promoted into actionable work while preserving the original source-linked memory record.
- [ ] Add completion states for action items such as `open`, `in_progress`, `blocked`, `completed`, `archived`, and `wont_do`.
- [ ] When an action item is completed, keep it searchable and visible in project history, graph context, Ask retrieval, and project briefs instead of deleting or hiding its knowledge value.
- [ ] Add completion metadata: completed_at, completion_note, outcome/decision, source links, and optional follow-up tasks/questions.
- [ ] Add UI controls to complete action items from native pages, project briefs, graph drawer, and extracted review panels.
- [ ] Add project brief sections for active action items, recently completed action items, blocked action items, and stale action items.
- [ ] Add Graphify rules that suggest action items from open questions, ideas without tasks, failed GitHub Actions runs, stale PRs, and unresolved project flags.
- [ ] Add a "Generate Prompt" action for tasks, open questions, ideas, decisions, project flags, GitHub issues/PRs, and action items.
- [ ] Use the configured local LLM to generate structured prompts that include objective, background, relevant source context, constraints, known decisions, open questions, acceptance criteria, and suggested next steps.
- [ ] Support prompt targets such as Codex, Claude, ChatGPT, generic engineering agent, and concise/manual mode.
- [ ] Let generated prompts include source citations and linked raw item IDs so pasted prompts preserve traceability.
- [ ] Add prompt preview/edit/copy UI and store generated prompts as source-linked artifacts for later reuse.
- [ ] Add tests for action item promotion, completion preservation, prompt payload assembly, and local-LLM prompt generation fallbacks.

## Connector And Import Backlog

- [ ] Add a generic connector model/service so every integration creates `RawItem`, optional `FileAsset`, and source metadata before processing.
- [ ] Add assistant/Codex session archive import: save full session transcripts as source records, extract decisions/tasks/questions/ideas, preserve repo/project/file metadata, and link sessions into the graph.
- [ ] Add Markdown folder import for Obsidian, Logseq, and plain `.md` note folders.
- [ ] Add local file import support for `.txt`, `.md`, `.html`, `.csv`, and `.json`.
- [ ] Add Google Drive import for docs, files, videos, and watched folders.
- [ ] Add NotebookLM import workflow: import original NotebookLM source files through Google Drive where possible, support manual upload of NotebookLM notes/briefing docs/study guides/FAQs/exported summaries, investigate shared/public notebook link ingestion, and preserve notebook title/source URL metadata.
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
- [ ] Add Flipboard saved-article import for saved/flipped articles via export, RSS/share links, or manual URL-list fallback.
- [ ] Add Readwise/Reader import for highlights, saved articles, and notes.
- [ ] Add Kindle highlights import.
- [ ] Add YouTube transcript import from video URLs.
- [ ] Add podcast transcript import from audio files or transcript URLs.
- [ ] Add meeting transcript import for Zoom, Google Meet, Otter, Fireflies, Granola, and similar exports.
- [x] Add PDF import with text extraction first, OCR later.
- [ ] Add `.epub` upload/import support with text extraction, metadata preservation, and chapter-aware source records.
- [ ] Add ebook import with text extraction first.
- [ ] Add long-document/book ingestion with document metadata, section/chapter/page chunking, per-chunk embeddings, staged extraction, and source-linked book notes.
- [ ] Add OCR for scanned PDFs/images later.
- [ ] Add Google Sheets ingestion:
  - Snapshot import for selected spreadsheet tabs/ranges.
  - Watched sheet sync for configured spreadsheet IDs/ranges, manual first and scheduled later.
  - Store `spreadsheet_sources` metadata and `table_artifacts` with columns, rows, range, row count, and content hash.
  - Support import modes: reference only, summarize only, row-per-memory, and extract tasks/questions.
  - Add Ask retrieval over sheet titles, headers, row summaries, and table artifacts with sheet/range citations.
- [ ] Add Excel import for `.xlsx` and `.csv` files.
- [ ] Add Airtable import for selected bases and tables.
- [ ] Add CRM export import for contacts, notes, tasks, and opportunities.
- [ ] Add Stripe export import for payments, customers, subscriptions, and business events.
- [ ] Add banking export import for CSV transaction files.
- [ ] Add support inbox import for support emails, tickets, and customer conversations.
- [ ] Add website analytics export import for traffic, conversions, and reporting snapshots.

## Bookmark And Read-Later Ingestion

- [ ] Add bookmark import from Chrome, Edge, Brave, Firefox, and Safari bookmark HTML exports.
- [ ] Add read-later import from Pocket, Instapaper, Raindrop, and Readwise Reader exports/APIs.
- [ ] Add manual URL-list paste/import flow.
- [ ] Parse bookmark title, URL, folder path, date added, source browser/import type, and optional notes.
- [ ] Add URL normalization and duplicate detection by canonicalized URL.
- [ ] Strip common tracking parameters such as `utm_*` during duplicate checks.
- [ ] Add reference-only import mode that stores bookmark metadata without fetching page content.
- [ ] Add optional fetch-and-analyze mode for page title, description, readable article text, and canonical URL.
- [ ] Add optional auto-process setting for imported bookmarks.
- [ ] Create `RawItem` records with `source_type=bookmark`, `source_uri=url`, and bookmark metadata.
- [ ] Preserve multiple bookmark folders/sources when the same URL appears more than once.
- [ ] Add bookmark dashboard/list view with filters for folder, domain, project, tag, source browser, status, date added, processed/unprocessed, and duplicate URL.
- [ ] Add read-later status values such as `unread`, `reading`, `reviewed`, and `archived`.
- [ ] Add batch process, archive, and assign-to-project controls for bookmarks.
- [ ] Add graph behavior for bookmark/source nodes, domain nodes, tags, projects, generated tasks, and raised questions.
- [ ] Add graph edges such as `from_domain`, `relates_to`, `tagged`, `suggested_task`, and `raises`.
- [ ] Add “why did I save this?” assistant workflow that infers likely purpose from page content and existing SecondBrain context.
- [ ] Add tests for Chrome/Firefox/Safari bookmark HTML parsing and URL duplicate normalization.

## Source-To-Markdown And Obsidian Export

- [ ] Add a source-to-Markdown converter service that can run independently from memory extraction.
- [ ] Convert PDF text into clean Markdown with source metadata.
- [ ] Convert EPUB books into Markdown chapters.
- [ ] Add DOCX-to-Markdown support.
- [ ] Add HTML/web-page-to-Markdown support.
- [ ] Convert email bodies and video/audio transcripts into Markdown source notes.
- [ ] Preserve title, author, source URL/file path, imported date, source type, and `raw_item_id` in frontmatter.
- [ ] Preserve page, chapter, section, or timestamp citations where available.
- [ ] Split long documents into chapter, section, page-range, or semantic-chunk files.
- [ ] Generate optional companion Markdown files for summaries, concepts, questions, highlights, tasks, decisions, and relationships.
- [ ] Add Obsidian export format with frontmatter, backlinks, source links, and vault-friendly folder layout.
- [ ] Add JSON Canvas-compatible export for reviewed graph relationships where useful.
- [ ] Add plain Markdown folder export for non-Obsidian use cases.
- [ ] Add CLI command shape: `secondbrain convert source.pdf --to markdown`.
- [ ] Add batch conversion for folders of PDFs, EPUBs, DOCX files, and HTML files.
- [ ] Add tests for source metadata preservation, chunk splitting, and Obsidian frontmatter/backlink output.

## Notion Export

- [ ] Add Notion as an optional publish/export target, distinct from local Markdown/Obsidian export.
- [ ] Store Notion integration token, parent page ID, and optional database IDs in local settings.
- [ ] Add a `notion_exports` tracking table for local entity type/id to Notion page/database row ID.
- [ ] Export individual memories as Notion pages.
- [ ] Export projects as Notion pages or database rows.
- [ ] Export tasks, decisions, and open questions as Notion database rows.
- [ ] Export source-to-Markdown packages into Notion page/block structures.
- [ ] Preserve `raw_item_id`, source URI, source type, memory ID, tags, project, timestamps, and confidence as Notion properties where possible.
- [ ] Store returned Notion page IDs so re-export updates existing pages instead of creating duplicates.
- [ ] Add manual export modes for one memory, one project, all reviewed records, and source-to-Markdown packages.
- [ ] Add export diagnostics for Notion API errors, rate limits, skipped records, and updated/created page counts.
- [ ] Add tests for Notion payload mapping without calling the live Notion API.

## Agent Context Integrations

- [ ] Add a "Save Session to Second Brain" workflow for Codex/Claude/ChatGPT sessions that stores raw transcript, summary, decisions, tasks, open questions, touched files, repo/branch metadata, and generated prompts.
- [x] Add an `agents/` or `integrations/agents/` directory with packaged install artifacts for Codex, MCP, CLI, and repo-local project mapping.
- [x] Add initial Codex agent Python scripts for project context extraction, Ask/search, saving session transcripts, and preview-gated task/decision creation.
- [x] Add agent scripts for project listing, prompt generation, and preview-gated open-question creation.
- [x] Add session-aware write-back using latest saved session state and a unified preview-gated `write_back.py`.
- [x] Add Codex agent operating instructions covering context fetch, prompt generation, session saving, write-back previews, and approval safety rules.
- [x] Add a Codex skill template that defines when to query SecondBrain, how to fetch project context, and how to record decisions/tasks back.
- [x] Add MCP server config templates for read-only and write-enabled modes.
- [ ] Add CLI environment/config templates for local `secondbrain` usage.
- [x] Add repo-local `.secondbrain.yml` template for mapping repositories to SecondBrain projects, tags, and search scopes.
- [x] Add install script or CLI command such as `secondbrain install-agent codex` that copies agent templates after explicit confirmation.
- [x] Make installed agent files user-editable while keeping repo-shipped templates versioned and replaceable.
- [x] Add agent installer update behavior that detects local modifications and offers keep, diff, backup-and-replace, or install-as-new options.
- [x] Add reset-to-default and diff-against-template commands for installed agent files.
- [x] Add user config overlay files such as `~/.config/secondbrain/agents/codex.yml` for common behavior settings without editing the full skill.
- [x] Add project-level `.secondbrain.yml` support for per-repo project scope, tags, write permissions, and search preferences.
- [x] Add safety documentation for read-only tools, write tools, approval gates, local allowlists, and avoiding silent agent config edits.
- [x] Add template validation tests or lint checks so packaged agent files stay usable.
- [ ] Add backend endpoints for project context lookup, semantic search, and creating notes/tasks/decisions from external tools.
- [ ] Add a local `secondbrain` CLI for `search`, `ask`, `project`, `add-note`, `add-task`, and `add-decision`.
- [x] Add a read-only MCP context server for `secondbrain_search`, `secondbrain_ask`, and `secondbrain_get_project_context`.
- [ ] Add MCP tools for fetching source-linked raw items, project tasks, decisions, open questions, and recent changes.
- [x] Add explicit approval gates before enabling MCP write tools.
- [x] Add MCP write tools for `secondbrain_create_note`, `secondbrain_create_task`, `secondbrain_record_decision`, and `secondbrain_create_open_question`.
- [x] Add a Codex skill that teaches Codex when and how to query Second Brain for project context before coding.
- [x] Add Codex skill workflows for pulling related decisions, tasks, open questions, and source notes.
- [x] Add Codex skill workflows for saving implementation decisions and follow-up tasks back to Second Brain.
- [x] Add support for repo-local `.secondbrain.yml` files that map code repos to Second Brain projects, tags, and search scopes.
- [ ] Add CLI/MCP authentication or local allowlist controls before exposing write actions.
- [ ] Add README documentation for using Second Brain as context memory for Codex and other local CLI agents.

## Built-In SecondBrain Agent

- [ ] Add an Agent Review page that can inspect inbox items, graph nodes, projects, tasks, decisions, and open questions.
- [ ] Add agent workflow to review the inbox and suggest action items.
- [ ] Add agent workflow to find orphaned graph nodes and suggest project/tag/relationship attachments.
- [ ] Add agent workflow to identify likely duplicate projects, tags, entities, and graph nodes.
- [ ] Add agent workflow to prepare project briefs from source-linked memories.
- [ ] Add agent workflow to answer open questions using stored context and source citations.
- [ ] Add agent workflow to suggest next steps for each active project.
- [ ] Add proposal UI where agent suggestions can be selected, edited, approved, or rejected before writes occur.
- [ ] Store agent runs, proposed actions, approved actions, rejected actions, and errors for auditability.

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
