from email.utils import parseaddr

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import EmailMessage, Idea, Memory, OpenQuestion, Project, RawItem, Relationship, Tag, Task
from app.models.decision import Decision
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


class GraphService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, show_archived: bool = False) -> GraphResponse:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        project_node_by_label: dict[str, str] = {}
        project_node_by_id: dict[str, str] = {}
        project_nodes: dict[str, GraphNode] = {}
        project_name_by_id: dict[str, str] = {}
        source_title_by_id: dict[str, str] = {}
        tags_by_memory_id: dict[str, list[str]] = {}
        ignored_labels_by_raw_item_id: dict[str, set[str]] = {}

        for project in self.db.scalars(select(Project)).all():
            normalized_name = self._normalize_label(project.name)
            node_id = project_node_by_label.get(normalized_name, f"project:{project.id}")
            project_nodes.setdefault(
                node_id,
                GraphNode(
                    id=node_id,
                    type="project",
                    label=project.name,
                    metadata={"project_id": project.id, "description": project.description},
                ),
            )
            project_node_by_id[project.id] = node_id
            project_name_by_id[project.id] = project.name
            project_node_by_label[normalized_name] = node_id
            project_node_by_label[self._normalize_label(f"{project.name} project")] = node_id

        task_query = select(Task)
        if not show_archived:
            task_query = task_query.where(Task.status != "archived")
        for task in self.db.scalars(task_query).all():
            node_id = f"task:{task.id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type="task",
                label=task.title,
                metadata=self._work_item_metadata(
                    task_id=task.id,
                    memory_id=task.memory_id,
                    project_id=task.project_id,
                    raw_item_id=task.source_raw_item_id,
                    status=task.status,
                    project_name_by_id=project_name_by_id,
                    source_title_by_id=source_title_by_id,
                    tags_by_memory_id=tags_by_memory_id,
                    description=task.description,
                    priority=task.priority,
                    due_date=task.due_date.isoformat() if task.due_date else None,
                ),
            )
            self._add_source_edge(nodes, edges, task.source_raw_item_id, node_id, project_nodes, project_node_by_label)
            if task.project_id:
                project_node_id = project_node_by_id.get(task.project_id, f"project:{task.project_id}")
                self._ensure_project_node(nodes, project_nodes, project_node_id)
                edges[f"project-task:{task.project_id}:{task.id}"] = GraphEdge(
                    id=f"project-task:{task.project_id}:{task.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has task",
                    relationship_type="has_task",
                )

        idea_query = select(Idea)
        if not show_archived:
            idea_query = idea_query.where(Idea.status != "archived")
        for idea in self.db.scalars(idea_query).all():
            node_id = f"idea:{idea.id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type="idea",
                label=idea.body[:80],
                metadata=self._work_item_metadata(
                    idea_id=idea.id,
                    memory_id=idea.memory_id,
                    project_id=idea.project_id,
                    raw_item_id=idea.source_raw_item_id,
                    status=idea.status,
                    project_name_by_id=project_name_by_id,
                    source_title_by_id=source_title_by_id,
                    tags_by_memory_id=tags_by_memory_id,
                    body=idea.body,
                ),
            )
            self._add_source_edge(nodes, edges, idea.source_raw_item_id, node_id, project_nodes, project_node_by_label)
            if idea.project_id:
                project_node_id = project_node_by_id.get(idea.project_id, f"project:{idea.project_id}")
                self._ensure_project_node(nodes, project_nodes, project_node_id)
                edges[f"project-idea:{idea.project_id}:{idea.id}"] = GraphEdge(
                    id=f"project-idea:{idea.project_id}:{idea.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has idea",
                    relationship_type="has_idea",
                )

        for decision in self.db.scalars(select(Decision)).all():
            node_id = f"decision:{decision.id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type="decision",
                label=decision.title,
                metadata=self._work_item_metadata(
                    decision_id=decision.id,
                    memory_id=decision.memory_id,
                    project_id=decision.project_id,
                    raw_item_id=decision.source_raw_item_id,
                    status="active",
                    project_name_by_id=project_name_by_id,
                    source_title_by_id=source_title_by_id,
                    tags_by_memory_id=tags_by_memory_id,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                    decided_at=decision.decided_at.isoformat() if decision.decided_at else None,
                ),
            )
            self._add_source_edge(nodes, edges, decision.source_raw_item_id, node_id, project_nodes, project_node_by_label)
            if decision.project_id:
                project_node_id = project_node_by_id.get(decision.project_id, f"project:{decision.project_id}")
                self._ensure_project_node(nodes, project_nodes, project_node_id)
                edges[f"project-decision:{decision.project_id}:{decision.id}"] = GraphEdge(
                    id=f"project-decision:{decision.project_id}:{decision.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has decision",
                    relationship_type="has_decision",
                )

        question_query = select(OpenQuestion)
        if not show_archived:
            question_query = question_query.where(OpenQuestion.status != "archived")
        for question in self.db.scalars(question_query).all():
            node_id = f"question:{question.id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type="question",
                label=question.question,
                metadata=self._work_item_metadata(
                    question_id=question.id,
                    memory_id=question.memory_id,
                    project_id=question.project_id,
                    raw_item_id=question.source_raw_item_id,
                    status=question.status,
                    project_name_by_id=project_name_by_id,
                    source_title_by_id=source_title_by_id,
                    tags_by_memory_id=tags_by_memory_id,
                ),
            )
            self._add_source_edge(nodes, edges, question.source_raw_item_id, node_id, project_nodes, project_node_by_label)
            if question.project_id:
                project_node_id = project_node_by_id.get(question.project_id, f"project:{question.project_id}")
                self._ensure_project_node(nodes, project_nodes, project_node_id)
                edges[f"project-question:{question.project_id}:{question.id}"] = GraphEdge(
                    id=f"project-question:{question.project_id}:{question.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has question",
                    relationship_type="has_question",
                )

        memories = self.db.scalars(
            select(Memory).options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.open_questions))
        ).all()
        decisions_by_memory_id: dict[str, list[Decision]] = {}
        for decision in self.db.scalars(select(Decision)).all():
            decisions_by_memory_id.setdefault(decision.memory_id, []).append(decision)

        for memory in memories:
            related_project_ids = {item.project_id for item in self._active_memory_items(memory, decisions_by_memory_id, show_archived) if item.project_id}
            related_project_node_ids = {project_node_by_id[project_id] for project_id in related_project_ids if project_id in project_node_by_id}
            raw_item = self.db.get(RawItem, memory.raw_item_id)
            matching_source_project_id = self._project_node_id_for_source(raw_item, project_nodes, project_node_by_label)
            if matching_source_project_id:
                related_project_node_ids.add(matching_source_project_id)
            fallback_source_node_id = self._source_node_id(memory.raw_item_id)
            ignored_source_labels = self._ignored_source_labels(memory.raw_item_id, ignored_labels_by_raw_item_id)

            for tag in memory.tags:
                if self._normalize_label(tag.name) in ignored_source_labels:
                    continue
                if self._normalize_label(tag.name) in project_node_by_label:
                    continue
                tag_node_id = f"tag:{tag.id}"
                nodes.setdefault(tag_node_id, GraphNode(id=tag_node_id, type="tag", label=tag.name, metadata={"tag_id": tag.id}))

                if related_project_node_ids:
                    for project_node_id in related_project_node_ids:
                        self._ensure_project_node(nodes, project_nodes, project_node_id)
                        edge_id = f"project-tag:{project_node_id}:{tag.id}"
                        edges.setdefault(
                            edge_id,
                            GraphEdge(id=edge_id, source=project_node_id, target=tag_node_id, label="tagged", relationship_type="tagged"),
                        )
                else:
                    nodes.setdefault(
                        fallback_source_node_id,
                        GraphNode(
                            id=fallback_source_node_id,
                            type="source",
                            label=raw_item.title if raw_item else "Source note",
                            metadata={"raw_item_id": memory.raw_item_id, **self._source_metadata(memory.raw_item_id)},
                        ),
                    )
                    edge_id = f"source-tag:{memory.raw_item_id}:{tag.id}"
                    edges.setdefault(
                        edge_id,
                        GraphEdge(id=edge_id, source=fallback_source_node_id, target=tag_node_id, label="tagged", relationship_type="tagged"),
                    )

        for rel in self.db.scalars(select(Relationship)).all():
            if not self.db.get(RawItem, rel.source_raw_item_id):
                continue
            ignored_source_labels = self._ignored_source_labels(rel.source_raw_item_id, ignored_labels_by_raw_item_id)
            if self._normalize_label(rel.source_label) in ignored_source_labels or self._normalize_label(rel.target_label) in ignored_source_labels:
                continue
            source_id = self._node_id_for_label(rel.source_label, rel.source_node_type, project_node_by_label)
            target_id = self._node_id_for_label(rel.target_label, rel.target_node_type, project_node_by_label)
            self._ensure_project_node(nodes, project_nodes, source_id)
            self._ensure_project_node(nodes, project_nodes, target_id)
            if source_id not in nodes:
                nodes[source_id] = GraphNode(
                    id=source_id,
                    type=rel.source_node_type,
                    label=rel.source_label,
                    metadata={"raw_item_id": rel.source_raw_item_id, **self._source_metadata(rel.source_raw_item_id)},
                )
            if target_id not in nodes:
                nodes[target_id] = GraphNode(
                    id=target_id,
                    type=rel.target_node_type,
                    label=rel.target_label,
                    metadata={"raw_item_id": rel.source_raw_item_id, **self._source_metadata(rel.source_raw_item_id)},
                )
            self._add_source_edge(nodes, edges, rel.source_raw_item_id, source_id, project_nodes, project_node_by_label)
            self._add_source_edge(nodes, edges, rel.source_raw_item_id, target_id, project_nodes, project_node_by_label)
            if source_id == target_id:
                continue
            edges[f"rel:{rel.id}"] = GraphEdge(
                id=f"rel:{rel.id}",
                source=source_id,
                target=target_id,
                label=rel.relationship_type,
                relationship_type=rel.relationship_type,
            )

        return self._pruned_response(nodes, edges)

    def _node_id_for_label(self, label: str, node_type: str, project_node_by_label: dict[str, str]) -> str:
        normalized = self._normalize_label(label)
        if normalized in project_node_by_label:
            return project_node_by_label[normalized]
        return f"{node_type}:{normalized.replace(' ', '-')}"

    def _normalize_label(self, label: str) -> str:
        normalized = " ".join(label.lower().strip().split())
        if normalized.endswith(" project"):
            normalized = normalized.removesuffix(" project").strip()
        return normalized

    def _source_node_id(self, raw_item_id: str) -> str:
        return f"source:{raw_item_id}"

    def _ensure_project_node(self, nodes: dict[str, GraphNode], project_nodes: dict[str, GraphNode], project_node_id: str) -> None:
        if project_node_id in project_nodes:
            nodes.setdefault(project_node_id, project_nodes[project_node_id])

    def _add_source_edge(
        self,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
        raw_item_id: str,
        target_node_id: str,
        project_nodes: dict[str, GraphNode],
        project_node_by_label: dict[str, str],
    ) -> None:
        raw_item = self.db.get(RawItem, raw_item_id)
        target_node = nodes.get(target_node_id)
        if raw_item and target_node and self._normalize_label(raw_item.title) == self._normalize_label(target_node.label):
            return
        source_node_id = self._project_node_id_for_source(raw_item, project_nodes, project_node_by_label) or self._source_node_id(raw_item_id)
        if source_node_id in project_nodes:
            self._ensure_project_node(nodes, project_nodes, source_node_id)
        else:
            nodes.setdefault(
                source_node_id,
                GraphNode(
                    id=source_node_id,
                    type="source",
                    label=raw_item.title if raw_item else "Source note",
                    metadata={"raw_item_id": raw_item_id, **self._source_metadata(raw_item_id)},
                ),
            )
        if source_node_id == target_node_id:
            return
        edge_id = f"source-derived:{raw_item_id}:{target_node_id}"
        edges.setdefault(
            edge_id,
            GraphEdge(id=edge_id, source=source_node_id, target=target_node_id, label="from source", relationship_type="from_source"),
        )

    def _project_node_id_for_source(self, raw_item: RawItem | None, project_nodes: dict[str, GraphNode], project_node_by_label: dict[str, str]) -> str | None:
        if not raw_item:
            return None
        project_node_id = project_node_by_label.get(self._normalize_label(raw_item.title))
        if project_node_id in project_nodes:
            return project_node_id
        return None

    def _work_item_metadata(
        self,
        *,
        memory_id: str,
        project_id: str | None,
        raw_item_id: str,
        status: str,
        project_name_by_id: dict[str, str],
        source_title_by_id: dict[str, str],
        tags_by_memory_id: dict[str, list[str]],
        **extra: object,
    ) -> dict:
        metadata = {
            "memory_id": memory_id,
            "project_id": project_id,
            "project_name": project_name_by_id.get(project_id or ""),
            "raw_item_id": raw_item_id,
            "source_title": self._source_title(raw_item_id, source_title_by_id),
            **self._source_metadata(raw_item_id),
            "status": status,
            "tags": self._memory_tags(memory_id, tags_by_memory_id),
        }
        metadata.update({key: value for key, value in extra.items() if value is not None})
        return metadata

    def _source_title(self, raw_item_id: str, source_title_by_id: dict[str, str]) -> str | None:
        if raw_item_id not in source_title_by_id:
            raw_item = self.db.get(RawItem, raw_item_id)
            source_title_by_id[raw_item_id] = raw_item.title if raw_item else ""
        return source_title_by_id[raw_item_id] or None

    def _source_metadata(self, raw_item_id: str) -> dict:
        raw_item = self.db.get(RawItem, raw_item_id)
        if not raw_item:
            return {}
        return {
            "source_type": raw_item.source_type,
            "source_created_at": raw_item.created_at.isoformat(),
        }

    def _memory_tags(self, memory_id: str, tags_by_memory_id: dict[str, list[str]]) -> list[str]:
        if memory_id not in tags_by_memory_id:
            memory = self.db.scalars(select(Memory).where(Memory.id == memory_id).options(selectinload(Memory.tags))).first()
            tags_by_memory_id[memory_id] = [tag.name for tag in memory.tags] if memory else []
        return tags_by_memory_id[memory_id]

    def _ignored_source_labels(self, raw_item_id: str, ignored_labels_by_raw_item_id: dict[str, set[str]]) -> set[str]:
        if raw_item_id in ignored_labels_by_raw_item_id:
            return ignored_labels_by_raw_item_id[raw_item_id]
        labels = set()
        raw_item = self.db.get(RawItem, raw_item_id)
        email = self.db.scalar(select(EmailMessage).where(EmailMessage.raw_item_id == raw_item_id))
        if email and email.from_email:
            sender_name, sender_email = parseaddr(email.from_email)
            for value in (sender_name, sender_email):
                normalized = self._normalize_label(value)
                if normalized:
                    labels.add(normalized)
        if raw_item and raw_item.source_type == "gmail":
            labels.update(self._signature_labels_from_body(raw_item.body_text))
        ignored_labels_by_raw_item_id[raw_item_id] = labels
        return labels

    def _signature_labels_from_body(self, body_text: str) -> set[str]:
        labels = set()
        lines = [line.strip().strip("*_") for line in body_text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
        if not lines:
            return labels
        candidate = lines[-1]
        if self._looks_like_signature_name(candidate):
            labels.add(self._normalize_label(candidate))
        return labels

    def _looks_like_signature_name(self, value: str) -> bool:
        if "@" in value or "://" in value or len(value) > 80:
            return False
        parts = value.replace(".", "").split()
        if len(parts) < 2 or len(parts) > 5:
            return False
        return all(part[:1].isupper() for part in parts if part)

    def _pruned_response(self, nodes: dict[str, GraphNode], edges: dict[str, GraphEdge]) -> GraphResponse:
        connected_node_ids = {edge.source for edge in edges.values()} | {edge.target for edge in edges.values()}
        context_only_types = {"tag", "entity", "person"}
        pruned_nodes = [
            node
            for node in nodes.values()
            if node.id in connected_node_ids or node.type not in context_only_types
        ]
        pruned_node_ids = {node.id for node in pruned_nodes}
        pruned_edges = [edge for edge in edges.values() if edge.source in pruned_node_ids and edge.target in pruned_node_ids]
        return GraphResponse(nodes=pruned_nodes, edges=pruned_edges)

    def _active_memory_items(self, memory: Memory, decisions_by_memory_id: dict[str, list[Decision]], show_archived: bool) -> list:
        items = [*memory.tasks, *memory.ideas, *memory.open_questions, *decisions_by_memory_id.get(memory.id, [])]
        if show_archived:
            return items
        return [item for item in items if getattr(item, "status", "active") != "archived"]
