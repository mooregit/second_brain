import json
import re
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
from app.services.settings_service import SettingsService


class ExtractionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.app_settings = SettingsService(db)
        self.ollama = OllamaClient()
        self.embedding_service = EmbeddingService(db)

    async def process_item(self, item: RawItem, run: ProcessingRun | None = None) -> Memory:
        item.status = "processing"
        extraction_model = self.app_settings.get_ollama_extraction_model()
        if run is None:
            run = ProcessingRun(raw_item_id=item.id, status="processing", model=extraction_model)
            self.db.add(run)
        else:
            run.status = "processing"
            run.model = extraction_model
            run.started_at = datetime.utcnow()
            run.finished_at = None
            run.error = None
        self.db.commit()

        media_context = MediaAnalysisService(self.db).analyze_raw_item(item)
        prompt_body = self._body_with_media_context(item.body_text, media_context)
        extraction_prompt = self._prompt("extraction.md").replace("{{title}}", item.title).replace("{{body}}", prompt_body)
        raw_output = ""
        try:
            raw_output = await self.ollama.generate(extraction_model, extraction_prompt)
            parsed = self._normalize_extraction_payload(self._parse_extraction_output(raw_output), item.title)
            result = ExtractionResult.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            repair_prompt = (
                self._prompt("extraction_repair.md")
                .replace("{{validation_error}}", str(exc))
                .replace("{{invalid_output}}", raw_output)
            )
            try:
                repaired_output = await self.ollama.generate(extraction_model, repair_prompt)
                parsed = self._normalize_extraction_payload(self._parse_extraction_output(repaired_output), item.title)
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

        result = self._enrich_sparse_knowledge_result(item, result)
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

    def _parse_extraction_output(self, output: str) -> dict:
        try:
            return self._parse(output)
        except json.JSONDecodeError:
            text = self._json_object_text(output)
            repaired = self._repair_common_json_issues(text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                fallback = self._fallback_extract_json_fields(text)
                if fallback:
                    return fallback
                raise

    def _json_object_text(self, output: str) -> str:
        text = output.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            return text[start : end + 1]
        return text

    def _repair_common_json_issues(self, text: str) -> str:
        repaired = re.sub(r",\s*([}\]])", r"\1", text)
        repaired = re.sub(r'"\s*\n\s*"', '",\n"', repaired)
        repaired = re.sub(r"}\s*\n\s*{", "},\n{", repaired)
        repaired = re.sub(r"]\s*\n\s*\"", '],\n"', repaired)
        repaired = re.sub(r"}\s*\n\s*\"", '},\n"', repaired)
        return repaired

    def _fallback_extract_json_fields(self, text: str) -> dict | None:
        payload: dict = {}
        summary = self._extract_json_string_field(text, "summary")
        if not summary:
            return None
        payload["summary"] = summary
        memory_type = self._extract_json_string_field(text, "memory_type")
        if memory_type:
            payload["memory_type"] = memory_type
        for key in ("projects", "people", "ideas", "open_questions", "tags", "entities", "suggested_actions"):
            payload[key] = self._extract_string_array_field(text, key)
        payload["tasks"] = self._extract_object_array_field(text, "tasks")
        payload["decisions"] = self._extract_object_array_field(text, "decisions")
        payload["relationships"] = self._extract_object_array_field(text, "relationships")
        confidence = self._extract_number_field(text, "confidence")
        if confidence is not None:
            payload["confidence"] = confidence
        return payload

    def _extract_json_string_field(self, text: str, key: str) -> str | None:
        match = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError:
            return match.group(1)

    def _extract_number_field(self, text: str, key: str) -> float | None:
        match = re.search(rf'"{re.escape(key)}"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text)
        return float(match.group(1)) if match else None

    def _extract_string_array_field(self, text: str, key: str) -> list[str]:
        array_text = self._extract_array_text(text, key)
        if not array_text:
            return []
        try:
            value = json.loads(array_text)
            return [item for item in value if isinstance(item, str)]
        except json.JSONDecodeError:
            return [match.group(1) for match in re.finditer(r'"((?:\\.|[^"\\])*)"', array_text)]

    def _extract_object_array_field(self, text: str, key: str) -> list[dict]:
        array_text = self._extract_array_text(text, key)
        if not array_text:
            return []
        try:
            value = json.loads(self._repair_common_json_issues(array_text))
            return [item for item in value if isinstance(item, dict)]
        except json.JSONDecodeError:
            objects = []
            for object_text in re.findall(r"\{[^{}]*\}", array_text, flags=re.DOTALL):
                try:
                    objects.append(json.loads(self._repair_common_json_issues(object_text)))
                except json.JSONDecodeError:
                    continue
            return objects

    def _extract_array_text(self, text: str, key: str) -> str | None:
        match = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
        if not match:
            return None
        start = match.end() - 1
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None

    def _normalize_extraction_payload(self, payload: dict, title: str) -> dict:
        normalized = dict(payload)
        normalized.setdefault("summary", self._summary_from_payload(normalized, title))
        normalized.setdefault("memory_type", "note")
        normalized.setdefault("projects", [])
        normalized.setdefault("people", [])
        normalized["tasks"] = self._normalize_tasks(normalized.get("tasks", []))
        normalized.setdefault("ideas", [])
        normalized["decisions"] = self._normalize_decisions(normalized.get("decisions", []))
        normalized.setdefault("open_questions", [])
        normalized.setdefault("tags", [])
        normalized.setdefault("entities", [])
        normalized["relationships"] = self._normalize_relationships(normalized.get("relationships", []))
        normalized.setdefault("suggested_actions", [])
        normalized.setdefault("confidence", 0.5)
        return normalized

    def _summary_from_payload(self, payload: dict, title: str) -> str:
        for key in ("summary", "title", "description", "overview", "main_idea"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("key_ai_trends", "topics", "sections", "items"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                labels = []
                for item in value[:3]:
                    if isinstance(item, dict):
                        label = item.get("title") or item.get("name") or item.get("summary")
                        if isinstance(label, str) and label.strip():
                            labels.append(label.strip())
                    elif isinstance(item, str) and item.strip():
                        labels.append(item.strip())
                if labels:
                    return "; ".join(labels)
        return title.strip() or "Imported item"

    def _normalize_tasks(self, tasks: object) -> list[dict]:
        if not isinstance(tasks, list):
            return []
        normalized = []
        for task in tasks:
            if isinstance(task, str) and task.strip():
                normalized.append({"title": task.strip(), "description": None, "priority": None, "due_date": None, "status": "open"})
            elif isinstance(task, dict):
                title = task.get("title") or task.get("task") or task.get("name")
                if isinstance(title, str) and title.strip():
                    normalized.append(
                        {
                            "title": title.strip(),
                            "description": task.get("description"),
                            "priority": task.get("priority"),
                            "due_date": task.get("due_date"),
                            "status": task.get("status") or "open",
                        }
                    )
        return normalized

    def _normalize_decisions(self, decisions: object) -> list[dict]:
        if not isinstance(decisions, list):
            return []
        normalized = []
        for decision in decisions:
            if isinstance(decision, str) and decision.strip():
                normalized.append({"title": decision.strip(), "rationale": None, "confidence": 0.5})
            elif isinstance(decision, dict):
                title = decision.get("title") or decision.get("decision") or decision.get("name")
                if isinstance(title, str) and title.strip():
                    normalized.append(
                        {
                            "title": title.strip(),
                            "rationale": decision.get("rationale"),
                            "confidence": decision.get("confidence", 0.5),
                        }
                    )
        return normalized

    def _normalize_relationships(self, relationships: object) -> list[dict]:
        if not isinstance(relationships, list):
            return []
        normalized = []
        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue
            source = relationship.get("source") or relationship.get("from")
            target = relationship.get("target") or relationship.get("to")
            label = relationship.get("relationship") or relationship.get("relationship_type") or relationship.get("type")
            if all(isinstance(value, str) and value.strip() for value in (source, target, label)):
                normalized.append({"source": source.strip(), "target": target.strip(), "relationship": label.strip()})
        return normalized

    def _enrich_sparse_knowledge_result(self, item: RawItem, result: ExtractionResult) -> ExtractionResult:
        if result.tasks or result.ideas or result.decisions or result.open_questions:
            return result
        if result.tags or result.entities or result.relationships:
            return result
        if item.source_type not in {"upload", "folder"} and result.memory_type not in {"resource", "file", "note"}:
            return result

        source_text = result.summary or item.body_text
        headings = self._extract_markdown_headings(source_text)
        terms_by_heading = self._extract_terms_by_heading(source_text)
        entities = self._unique([term for terms in terms_by_heading.values() for term in terms])
        tags = self._unique(headings)
        if len(entities) < 3:
            return result

        relationships = [
            {"source": heading, "target": term, "relationship": "includes"}
            for heading, terms in terms_by_heading.items()
            for term in terms[:12]
            if heading in tags
        ]
        enriched_payload = result.model_dump(mode="json")
        enriched_payload.update(
            {
                "memory_type": "resource" if result.memory_type == "note" else result.memory_type,
                "tags": tags[:12],
                "entities": entities[:80],
                "relationships": relationships[:120],
            }
        )
        return ExtractionResult.model_validate(enriched_payload)

    def _extract_markdown_headings(self, text: str) -> list[str]:
        headings = []
        for line in text.splitlines():
            stripped = line.strip().strip("*")
            match = re.match(r"^#{2,4}\s+(.+)$", stripped)
            if match:
                headings.append(self._clean_knowledge_label(match.group(1)))
        return self._unique([heading for heading in headings if heading])

    def _extract_terms_by_heading(self, text: str) -> dict[str, list[str]]:
        current_heading: str | None = None
        terms_by_heading: dict[str, list[str]] = {}
        for line in text.splitlines():
            stripped = line.strip()
            heading_match = re.match(r"^#{2,4}\s+\**(.+?)\**\s*$", stripped)
            if heading_match:
                current_heading = self._clean_knowledge_label(heading_match.group(1))
                if current_heading:
                    terms_by_heading.setdefault(current_heading, [])
                continue
            if not current_heading:
                continue
            term = self._term_from_definition_line(stripped)
            if term:
                terms_by_heading.setdefault(current_heading, []).append(term)
        return {heading: self._unique(terms) for heading, terms in terms_by_heading.items() if terms}

    def _term_from_definition_line(self, line: str) -> str | None:
        patterns = [
            r"^[-*]\s+\*\*(.+?)\*\*\s*:",
            r"^[-*]\s+(.+?)\s*:",
        ]
        for pattern in patterns:
            match = re.match(pattern, line)
            if not match:
                continue
            term = self._clean_knowledge_label(match.group(1))
            if term and 2 <= len(term) <= 80:
                return term
        return None

    def _clean_knowledge_label(self, value: str) -> str:
        return value.strip().strip("*`:- ")

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        unique_values = []
        for value in values:
            normalized = self._normalize_lookup(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_values.append(value)
        return unique_values

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
