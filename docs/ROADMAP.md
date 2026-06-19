# Roadmap

This roadmap describes likely product directions after the current Second Brain Inbox loop is stable.

## Product Direction

Second Brain Inbox should remain focused on local-first personal/work knowledge capture:

- Bring in raw information from notes, files, Gmail, folders, and future connectors.
- Extract structured memories, projects, tasks, decisions, ideas, questions, tags, and relationships.
- Keep source traceability from every extracted record back to the raw item.
- Make memory searchable through Ask, project views, review screens, and graph exploration.

Future work should improve this core loop before expanding into separate product modes.

## Obsidian Positioning

Second Brain Inbox should not try to beat Obsidian as a note editor. Obsidian is a mature local-first writing, linking, clipping, and knowledge workspace. Second Brain Inbox should instead be positioned as a local AI ingestion and extraction engine that can either stand alone or export into Obsidian.

A strong future direction is:

> Process everything in Second Brain Inbox, then export reviewed memories to an Obsidian vault as Markdown with frontmatter, backlinks, source links, and Canvas/graph-compatible relationship data.

This means Obsidian integration should focus on interoperability:

- Export reviewed memories, projects, tasks, ideas, decisions, and open questions as Markdown files.
- Preserve source links and raw-item traceability in frontmatter.
- Generate backlinks between exported records.
- Optionally emit JSON Canvas-compatible graph data for visual review in Obsidian.
- Treat Obsidian as a durable writing and knowledge workspace, not as a feature-for-feature competitor.

## Source-To-Markdown Pipeline

A related product direction is a source-to-Markdown converter that turns durable but hard-to-work-with sources into clean Markdown and optional structured memories.

This should support standalone export use cases and Obsidian interoperability:

- Convert PDFs, EPUBs, DOCX files, HTML, web pages, emails, transcripts, and video transcripts into readable Markdown.
- Preserve source metadata such as title, author, source URL/file path, imported date, page/chapter/section references, and Second Brain raw item IDs.
- Split long sources into stable files by chapter, section, page range, or semantic chunk.
- Add frontmatter and stable anchors for citation/backlink use.
- Optionally generate companion files for summaries, concepts, questions, highlights, tasks, decisions, and relationships.
- Export to an Obsidian vault, plain Markdown folder, Git-backed docs folder, or Second Brain memory records.

For books, the valuable version is not simple PDF-to-text. It should produce a structured Markdown package:

```text
Book/PDF/EPUB
-> clean Markdown chapters
-> frontmatter
-> source/page citations
-> chapter summaries
-> concepts/entities
-> extracted questions
-> optional Obsidian backlinks
```

Example export shape:

```text
vault/
  Sources/
    Book Name/
      index.md
      chapter-01.md
      chapter-02.md
      concepts.md
      questions.md
      highlights.md
```

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
- Structured table ingestion for Google Sheets and CSV-like sources, including table artifacts, watched ranges, import modes, and range-level Ask citations.
- NotebookLM import workflows for original Drive-backed sources, saved notes/briefing docs/study guides/FAQs/exported summaries, and shared/public notebook links.
- Notion pages and databases through the official Notion API.
- GitHub issues, pull requests, comments, project boards, and commits.
- Readwise/Reader, Kindle highlights, RSS feeds, browser bookmarks, Pocket, Instapaper, and Raindrop.
- Slack, Discord, Linear, Jira, Trello, Airtable, CRM exports, support inboxes, Stripe exports, banking CSVs, and website analytics exports.

## Agent Context Integrations

Second Brain should eventually act as context memory for local coding agents and CLI tools.

### MCP Context Server

The first agent-facing surface should be a controlled context server rather than a fully autonomous agent. An MCP server would let Codex, Claude Desktop, local CLI agents, and future tools query Second Brain through a stable interface.

Planned surfaces:

- Local `secondbrain` CLI with commands such as `search`, `ask`, `project`, `add-note`, `add-task`, and `add-decision`.
- MCP server exposing tools such as `secondbrain_search`, `secondbrain_ask`, `secondbrain_get_project_context`, `secondbrain_create_note`, `secondbrain_create_task`, and `secondbrain_record_decision`.
- Codex skill that teaches Codex when to query Second Brain for project context and when to write decisions or follow-up tasks back.
- Repo-local `.secondbrain.yml` files that map code repositories to Second Brain projects, tags, and search scopes.
- Local allowlist/auth controls before exposing write actions.

Read-only tools should come first:

- Search memories, projects, tasks, decisions, and questions.
- Fetch project context.
- Fetch source-linked raw items.
- Ask a retrieval-grounded question against Second Brain.

Write tools should require explicit local approval at first:

- Create notes.
- Create tasks.
- Record decisions.
- Add open questions.
- Save implementation follow-ups from coding agents.

### Built-In SecondBrain Agent

After the MCP/context layer is useful, add an in-app agent that uses the same tools but works inside the Second Brain UI.

Initial agent workflows:

- Review the inbox and suggest what needs action.
- Find orphaned graph nodes and propose relationships.
- Summarize what changed this week.
- Suggest duplicate project/tag/entity merges.
- Turn an email, video, file, or PDF into project tasks.
- Prepare project briefs from stored memories and sources.
- Answer open questions using stored context.
- Suggest next steps for active projects.

The built-in agent should be proposal-first, not autonomous. It should present suggested changes and let the user approve selected actions before anything is written.

Example:

```text
Agent suggestion:
- Merge "company workflows" into "Workflow Imagination"
- Attach "video analysis" to "Workflow Imagination"
- Create task: "Review workflow automation opportunities"
- Archive duplicate node: "Workflow imagination involves visualizing multi-step processes"

[Apply selected]
```

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
