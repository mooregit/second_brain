from collections import Counter, defaultdict
from difflib import SequenceMatcher
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, Idea, OpenQuestion, Project, RawItem, Relationship, Tag, Task
from app.schemas.graph import (
    GraphDuplicateCandidate,
    GraphInsightsResponse,
    GraphProjectSummary,
    GraphRelationshipNormalization,
    GraphUnassignedWorkItem,
)
from app.services.graph_service import GraphService


RELATIONSHIP_ALIASES = {
    "related to": "related_to",
    "related-to": "related_to",
    "relates to": "related_to",
    "needs": "requires",
    "need": "requires",
    "requires": "requires",
    "require": "requires",
    "depends on": "depends_on",
    "depends-on": "depends_on",
    "depends_on": "depends_on",
    "blocked by": "blocked_by",
    "blocked_by": "blocked_by",
    "blocks": "blocks",
    "may affect": "may_affect",
    "may_affect": "may_affect",
    "could affect": "may_affect",
    "affects": "affects",
    "shows": "shows",
    "show": "shows",
    "displays": "shows",
    "answers": "answers",
    "answers question": "answers",
    "supersedes": "supersedes",
    "owned by": "owned_by",
    "owned_by": "owned_by",
}


class GraphInsightsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, show_archived: bool = False) -> GraphInsightsResponse:
        graph = GraphService(self.db).build(show_archived=show_archived)
        return GraphInsightsResponse(
            duplicate_candidates=self._duplicate_candidates(graph.nodes),
            relationship_normalizations=self._relationship_normalizations(),
            unassigned_work_items=self._unassigned_work_items(show_archived=show_archived),
            project_summaries=self._project_summaries(show_archived=show_archived),
        )

    def _duplicate_candidates(self, nodes: list) -> list[GraphDuplicateCandidate]:
        candidates: list[GraphDuplicateCandidate] = []
        by_type: dict[str, list] = defaultdict(list)
        for node in nodes:
            if node.type in {"project", "tag", "entity", "person"}:
                by_type[node.type].append(node)

        for node_type, typed_nodes in by_type.items():
            exact_groups: dict[str, list] = defaultdict(list)
            for node in typed_nodes:
                exact_groups[self._dedupe_key(node.label)].append(node)
            for key, grouped_nodes in exact_groups.items():
                if key and len(grouped_nodes) > 1:
                    candidates.append(self._candidate(node_type, grouped_nodes, "Same normalized label"))

            seen_pairs: set[tuple[str, str]] = set()
            for index, left in enumerate(typed_nodes):
                left_key = self._dedupe_key(left.label)
                if not left_key:
                    continue
                for right in typed_nodes[index + 1:]:
                    right_key = self._dedupe_key(right.label)
                    pair_key = tuple(sorted((left.id, right.id)))
                    if pair_key in seen_pairs or not right_key or left_key == right_key:
                        continue
                    if self._looks_like_duplicate(left_key, right_key):
                        seen_pairs.add(pair_key)
                        candidates.append(self._candidate(node_type, [left, right], "Very similar labels"))

        candidates.sort(key=lambda candidate: (candidate.node_type, candidate.canonical_label))
        return candidates[:20]

    def _relationship_normalizations(self) -> list[GraphRelationshipNormalization]:
        counts: Counter[tuple[str, str]] = Counter()
        for relationship in self.db.scalars(select(Relationship)).all():
            normalized = self.normalize_relationship_type(relationship.relationship_type)
            if relationship.relationship_type != normalized:
                counts[(relationship.relationship_type, normalized)] += 1
        return [
            GraphRelationshipNormalization(original_type=original, normalized_type=normalized, count=count)
            for (original, normalized), count in sorted(counts.items(), key=lambda item: (-item[1], item[0][0]))
        ]

    def _unassigned_work_items(self, show_archived: bool) -> list[GraphUnassignedWorkItem]:
        items: list[GraphUnassignedWorkItem] = []
        task_query = select(Task).where(Task.project_id.is_(None))
        idea_query = select(Idea).where(Idea.project_id.is_(None))
        question_query = select(OpenQuestion).where(OpenQuestion.project_id.is_(None))
        if not show_archived:
            task_query = task_query.where(Task.status != "archived")
            idea_query = idea_query.where(Idea.status != "archived")
            question_query = question_query.where(OpenQuestion.status != "archived")

        for task in self.db.scalars(task_query).all():
            items.append(GraphUnassignedWorkItem(id=task.id, type="task", label=task.title, memory_id=task.memory_id, source_title=self._source_title(task.source_raw_item_id)))
        for idea in self.db.scalars(idea_query).all():
            items.append(GraphUnassignedWorkItem(id=idea.id, type="idea", label=idea.body[:80], memory_id=idea.memory_id, source_title=self._source_title(idea.source_raw_item_id)))
        for question in self.db.scalars(question_query).all():
            items.append(GraphUnassignedWorkItem(id=question.id, type="question", label=question.question, memory_id=question.memory_id, source_title=self._source_title(question.source_raw_item_id)))
        for decision in self.db.scalars(select(Decision).where(Decision.project_id.is_(None))).all():
            items.append(GraphUnassignedWorkItem(id=decision.id, type="decision", label=decision.title, memory_id=decision.memory_id, source_title=self._source_title(decision.source_raw_item_id)))

        items.sort(key=lambda item: (item.type, item.label.lower()))
        return items[:25]

    def _project_summaries(self, show_archived: bool) -> list[GraphProjectSummary]:
        summaries: list[GraphProjectSummary] = []
        for project in self.db.scalars(select(Project)).all():
            open_tasks = sum(1 for task in project.tasks if show_archived or task.status != "archived")
            open_questions = sum(1 for question in project.open_questions if show_archived or question.status != "archived")
            active_ideas = sum(1 for idea in project.ideas if show_archived or idea.status != "archived")
            decisions = len(project.decisions)
            risk_flags = []
            if open_questions and not decisions:
                risk_flags.append("questions_without_decisions")
            if active_ideas and not open_tasks:
                risk_flags.append("ideas_without_tasks")
            if open_tasks == 0 and open_questions == 0 and active_ideas == 0 and decisions == 0:
                risk_flags.append("empty_project")
            summaries.append(
                GraphProjectSummary(
                    project_id=project.id,
                    name=project.name,
                    open_tasks=open_tasks,
                    open_questions=open_questions,
                    active_ideas=active_ideas,
                    decisions=decisions,
                    risk_flags=risk_flags,
                )
            )
        summaries.sort(key=lambda summary: (len(summary.risk_flags) == 0, -summary.open_questions, -summary.open_tasks, summary.name.lower()))
        return summaries[:25]

    def _source_title(self, raw_item_id: str) -> str | None:
        raw_item = self.db.get(RawItem, raw_item_id)
        return raw_item.title if raw_item else None

    def _candidate(self, node_type: str, nodes: list, reason: str) -> GraphDuplicateCandidate:
        labels = sorted({node.label for node in nodes}, key=str.lower)
        return GraphDuplicateCandidate(
            node_type=node_type,
            canonical_label=labels[0],
            labels=labels,
            node_ids=[node.id for node in nodes],
            reason=reason,
        )

    def _looks_like_duplicate(self, left: str, right: str) -> bool:
        if len(left) < 5 or len(right) < 5:
            return False
        if left in right or right in left:
            shorter = min(len(left), len(right))
            longer = max(len(left), len(right))
            return shorter / longer >= 0.72
        return SequenceMatcher(None, left, right).ratio() >= 0.88

    def _dedupe_key(self, label: str) -> str:
        normalized = " ".join(label.lower().strip().split())
        normalized = normalized.rstrip("/")
        if normalized.endswith(" project"):
            normalized = normalized.removesuffix(" project").strip()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(normalized.split())

    @staticmethod
    def normalize_relationship_type(relationship_type: str) -> str:
        normalized = " ".join(relationship_type.lower().strip().replace("_", " ").split())
        if normalized in RELATIONSHIP_ALIASES:
            return RELATIONSHIP_ALIASES[normalized]
        return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "related_to"
