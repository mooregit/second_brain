import json
from datetime import date, datetime
from email.utils import parseaddr

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Decision, EmailMessage, Idea, Memory, OpenQuestion, Person, ProcessingRun, Project, RawItem, Relationship, Tag, Task
from app.schemas.extraction import ExtractionResult
from app.services.embedding_service import EmbeddingService
from app.services.media_analysis_service import MediaAnalysisService
from app.services.ollama_client import OllamaClient


class ExtractionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.ollama = OllamaClient()
        self.embedding_service = EmbeddingService(db)

    async def process_item(self, item: RawItem) -> Memory:
        item.status = "processing"
        run = ProcessingRun(raw_item_id=item.id, status="started", model=self.settings.ollama_extraction_model)
        self.db.add(run)
        self.db.commit()

        media_context = MediaAnalysisService(self.db).analyze_raw_item(item)
        prompt_body = self._body_with_media_context(item.body_text, media_context)
        extraction_prompt = self._prompt("extraction.md").replace("{{title}}", item.title).replace("{{body}}", prompt_body)
        raw_output = ""
        try:
            raw_output = await self.ollama.generate(self.settings.ollama_extraction_model, extraction_prompt)
            parsed = self._parse(raw_output)
            result = ExtractionResult.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            repair_prompt = (
                self._prompt("extraction_repair.md")
                .replace("{{validation_error}}", str(exc))
                .replace("{{invalid_output}}", raw_output)
            )
            try:
                repaired_output = await self.ollama.generate(self.settings.ollama_extraction_model, repair_prompt)
                parsed = self._parse(repaired_output)
                result = ExtractionResult.model_validate(parsed)
                raw_output = f"{raw_output}\n\n--- repaired ---\n{repaired_output}"
            except (json.JSONDecodeError, ValidationError, Exception) as repair_exc:
                item.status = "failed"
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.error = str(repair_exc)
                run.raw_output = raw_output
                self.db.commit()
                raise RuntimeError(f"Extraction failed: {repair_exc}") from repair_exc
        except Exception as exc:
            item.status = "failed"
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(exc)
            run.raw_output = raw_output
            self.db.commit()
            raise RuntimeError(f"Ollama extraction failed: {exc}") from exc

        memory = self._persist_result(item, result, raw_output)
        run.status = "succeeded"
        run.finished_at = datetime.utcnow()
        run.raw_output = raw_output
        run.parsed_json = result.model_dump(mode="json")
        item.status = "processed"
        self.db.commit()
        self.db.refresh(memory)

        await self._embed_records(memory)
        return memory

    def _persist_result(self, item: RawItem, result: ExtractionResult, raw_output: str) -> Memory:
        memory = Memory(
            raw_item_id=item.id,
            memory_type=result.memory_type,
            summary=result.summary,
            confidence=result.confidence,
            validated_json=result.model_dump(mode="json"),
            raw_llm_output=raw_output,
        )
        self.db.add(memory)
        self.db.flush()

        projects = [self._get_or_create_project(name) for name in result.projects if name.strip()]
        project = projects[0] if projects else None
        ignored_labels = self._ignored_source_labels(item)

        for tag_name in set([*result.tags, *result.projects]):
            tag_name = tag_name.strip()
            if tag_name and self._normalize_lookup(tag_name) not in ignored_labels:
                memory.tags.append(self._get_or_create_tag(tag_name))

        for person_name in result.people:
            person_name = person_name.strip()
            if person_name and self._normalize_lookup(person_name) not in ignored_labels:
                self._get_or_create_person(person_name)

        for task in result.tasks:
            self.db.add(
                Task(
                    memory_id=memory.id,
                    project_id=project.id if project else None,
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    status=task.status or "open",
                    due_date=self._parse_date(task.due_date),
                    source_raw_item_id=item.id,
                )
            )
        for idea in result.ideas:
            self.db.add(Idea(memory_id=memory.id, project_id=project.id if project else None, body=idea, source_raw_item_id=item.id))
        for decision in result.decisions:
            self.db.add(
                Decision(
                    memory_id=memory.id,
                    project_id=project.id if project else None,
                    title=decision.title,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                    source_raw_item_id=item.id,
                )
            )
        for question in result.open_questions:
            self.db.add(
                OpenQuestion(memory_id=memory.id, project_id=project.id if project else None, question=question, source_raw_item_id=item.id)
            )
        for relationship in result.relationships:
            if self._normalize_lookup(relationship.source) in ignored_labels or self._normalize_lookup(relationship.target) in ignored_labels:
                continue
            self.db.add(
                Relationship(
                    memory_id=memory.id,
                    source_label=relationship.source,
                    target_label=relationship.target,
                    relationship_type=relationship.relationship,
                    source_raw_item_id=item.id,
                )
            )
        return memory

    async def _embed_records(self, memory: Memory) -> None:
        await self.embedding_service.embed_owner("memory", memory.id, memory.summary)
        for task in memory.tasks:
            await self.embedding_service.embed_owner("task", task.id, f"{task.title}\n{task.description or ''}")
        for idea in memory.ideas:
            await self.embedding_service.embed_owner("idea", idea.id, idea.body)
        for decision in memory.decisions:
            await self.embedding_service.embed_owner("decision", decision.id, f"{decision.title}\n{decision.rationale or ''}")
        for question in memory.open_questions:
            await self.embedding_service.embed_owner("open_question", question.id, question.question)

    def _get_or_create_project(self, name: str) -> Project:
        normalized = name.strip()
        lookup = self._normalize_lookup(normalized)
        for project in self.db.scalars(select(Project)).all():
            if self._normalize_lookup(project.name) == lookup:
                return project
        project = Project(name=normalized)
        self.db.add(project)
        self.db.flush()
        return project

    def _get_or_create_tag(self, name: str) -> Tag:
        normalized = name.strip()
        lookup = " ".join(normalized.lower().split())
        for tag in self.db.scalars(select(Tag)).all():
            if " ".join(tag.name.lower().split()) == lookup:
                return tag
        tag = Tag(name=normalized)
        self.db.add(tag)
        self.db.flush()
        return tag

    def _get_or_create_person(self, name: str) -> Person:
        normalized = name.strip()
        lookup = self._normalize_lookup(normalized)
        for person in self.db.scalars(select(Person)).all():
            if self._normalize_lookup(person.name) == lookup:
                return person
        person = Person(name=normalized)
        self.db.add(person)
        self.db.flush()
        return person

    def _normalize_lookup(self, value: str) -> str:
        normalized = " ".join(value.lower().strip().split())
        if normalized.endswith(" project"):
            normalized = normalized.removesuffix(" project").strip()
        return normalized

    def _ignored_source_labels(self, item: RawItem) -> set[str]:
        ignored = set()
        if item.source_type != "gmail":
            return ignored
        email = self.db.scalar(select(EmailMessage).where(EmailMessage.raw_item_id == item.id))
        if not email or not email.from_email:
            return ignored
        sender_name, sender_email = parseaddr(email.from_email)
        for value in (sender_name, sender_email):
            normalized = self._normalize_lookup(value)
            if normalized:
                ignored.add(normalized)
        ignored.update(self._signature_labels_from_body(item.body_text))
        return ignored

    def _signature_labels_from_body(self, body_text: str) -> set[str]:
        labels = set()
        lines = [line.strip().strip("*_") for line in body_text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
        if not lines:
            return labels
        candidate = lines[-1]
        if self._looks_like_signature_name(candidate):
            labels.add(self._normalize_lookup(candidate))
        return labels

    def _looks_like_signature_name(self, value: str) -> bool:
        if "@" in value or "://" in value or len(value) > 80:
            return False
        parts = value.replace(".", "").split()
        if len(parts) < 2 or len(parts) > 5:
            return False
        return all(part[:1].isupper() for part in parts if part)

    def _prompt(self, filename: str) -> str:
        return (self.settings.prompt_dir / filename).read_text(encoding="utf-8")

    def _parse(self, output: str) -> dict:
        text = output.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]
        return json.loads(text)

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _body_with_media_context(self, body_text: str, media_context: str) -> str:
        if not media_context:
            return body_text
        return f"{body_text.rstrip()}\n\n--- Media Analysis ---\n{media_context}".strip()
