# Roadmap

This roadmap describes likely product directions after the current Second Brain Inbox loop is stable.

## Product Direction

Second Brain Inbox should remain focused on local-first personal/work knowledge capture:

- Bring in raw information from notes, files, Gmail, folders, and future connectors.
- Extract structured memories, projects, tasks, decisions, ideas, questions, tags, and relationships.
- Keep source traceability from every extracted record back to the raw item.
- Make memory searchable through Ask, project views, review screens, and graph exploration.

Future work should improve this core loop before expanding into separate product modes.

## Near-Term Priorities

1. Connector dashboard
   - Add a "Ways to bring in data" area near the Inbox.
   - Show Manual Note, Upload File, Scan Folder, Sync Gmail, Apple Notes export, and planned connectors.
   - Show setup status, last sync result, last error, and next action for each source.

2. Processing queue
   - Move long-running imports and processing behind explicit jobs.
   - Track `pending`, `processing`, `processed`, and `failed` states.
   - Add retry, cancel, and reprocess actions.

3. Review and cleanup
   - Improve edit/delete/archive controls across memories, projects, tasks, ideas, decisions, and questions.
   - Add project reassignment outside the graph drawer.
   - Add duplicate detection and merge workflows for projects, tags, people, URLs, and entities.

4. Project workspaces
   - Build stronger project detail pages.
   - Include timeline, source notes/emails/files, open tasks, open questions, decisions, ideas, and a related graph slice.

5. Ask improvements
   - Show retrieved context.
   - Add filters by project, source type, tag, and date range.
   - Let useful Ask answers become memories, decisions, tasks, or open questions.

## Connector Expansion

Prioritize connectors that fit the local-first model and create `RawItem`, optional `FileAsset`, and metadata records before processing:

- Markdown folders, Obsidian, Logseq, and plain `.md` note folders.
- Local files: `.txt`, `.md`, `.html`, `.csv`, `.json`, PDFs, and ebooks.
- Whole-book ingestion for PDFs/EPUBs with document metadata, chapter/page/section chunking, per-chunk embeddings, staged concept extraction, and source-linked notes.
- Apple Notes/iCloud Notes through export-to-folder or share-to-email workflows.
- Google Drive, Google Docs, Google Calendar, and Google Sheets.
- NotebookLM import workflows for original Drive-backed sources, saved notes/briefing docs/study guides/FAQs/exported summaries, and shared/public notebook links.
- Notion pages and databases through the official Notion API.
- GitHub issues, pull requests, comments, project boards, and commits.
- Readwise/Reader, Kindle highlights, RSS feeds, browser bookmarks, Pocket, Instapaper, and Raindrop.
- Slack, Discord, Linear, Jira, Trello, Airtable, CRM exports, support inboxes, Stripe exports, banking CSVs, and website analytics exports.

## Agent Context Integrations

Second Brain should eventually act as context memory for local coding agents and CLI tools.

Planned surfaces:

- Local `secondbrain` CLI with commands such as `search`, `ask`, `project`, `add-note`, `add-task`, and `add-decision`.
- MCP server exposing tools such as `secondbrain_search`, `secondbrain_ask`, `secondbrain_get_project_context`, `secondbrain_create_note`, `secondbrain_create_task`, and `secondbrain_record_decision`.
- Codex skill that teaches Codex when to query Second Brain for project context and when to write decisions or follow-up tasks back.
- Repo-local `.secondbrain.yml` files that map code repositories to Second Brain projects, tags, and search scopes.
- Local allowlist/auth controls before exposing write actions.

## Future Platform Module: Developmental Learning Agent

The developmental AI learning agent idea should be treated as a sibling platform/module, not as a direct expansion of the core Second Brain Inbox UI.

### Product Boundary

Second Brain is about the user's memory, work, projects, and source traceability.

The developmental learning agent is about the AI's curriculum, staged growth, feedback, confidence, evaluation, and consolidation.

They should share infrastructure where possible, but the user experience and domain models should stay separate enough that Second Brain does not become cluttered with agent-training concepts.

### Shared Infrastructure

The learning agent can reuse:

- FastAPI backend patterns.
- Postgres and pgvector.
- Ollama/API LLM client abstraction.
- File ingestion and raw item storage.
- Extraction and JSON repair pipeline.
- Embeddings and semantic retrieval.
- React/Vite/Tailwind frontend stack.
- React Flow graph visualization.
- Source traceability.
- Processing runs and future queue infrastructure.
- Future consolidation/sleep jobs.

### New Domain Concepts

The learning agent likely needs its own models and workflows:

- `LearningSession`
- `Concept`
- `Fact`
- `ConceptRelationship`
- `Contradiction`
- `UserFeedback`
- `LearningStage`
- `StageEvaluation`
- `Quiz`
- `QuizQuestion`
- `AgentSkill`
- `ConsolidationRun`
- `RewardSignal`

### MVP Shape

The first version of the learning agent should include:

1. Chat/Teach mode.
2. File upload and text ingestion.
3. Concept, fact, and relationship extraction.
4. Persistent memory storage.
5. Interactive mind map visualization.
6. Feedback buttons for correct, wrong, partially correct, useful, confusing, and unsupported answers.
7. Memory confidence scoring.
8. Manual or scheduled sleep/consolidation job.
9. Basic learning stages and progress tracking.
10. Future answers grounded in stored memory.

### Staged Development

Learning stages should advance only after basic evaluation checks pass.

Possible stages:

1. Store and recall facts.
2. Link related concepts.
3. Ask clarifying questions.
4. Read and summarize documents.
5. Detect contradictions.
6. Generate quizzes.
7. Track confidence and user feedback.
8. Recommend what to learn next.
9. Plan tasks from learned knowledge.

### Sleep/Consolidation Cycle

The sleep cycle should run manually at first, then become schedulable.

It should:

- Summarize new memories.
- Merge duplicates.
- Update confidence scores.
- Detect contradictions.
- Generate review questions.
- Recommend what the AI should learn next.
- Record consolidation outputs for auditability.

### Recommended Path

Do not build the developmental learning agent until Second Brain has these primitives in place:

- Processing queue.
- Better extraction diagnostics.
- Generic connector model.
- Concept/fact/relationship schema.
- Feedback event storage.
- Consolidation job framework.
- Graph cleanup and merge tooling.

Once those exist, start the learning agent as a separate app surface or module that uses the shared backend infrastructure.
