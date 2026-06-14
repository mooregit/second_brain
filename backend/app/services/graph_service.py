from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Idea, Memory, OpenQuestion, Project, RawItem, Relationship, Tag, Task
from app.models.decision import Decision
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


class GraphService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self) -> GraphResponse:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        project_node_by_label: dict[str, str] = {}
        project_node_by_id: dict[str, str] = {}

        for project in self.db.scalars(select(Project)).all():
            normalized_name = self._normalize_label(project.name)
            node_id = project_node_by_label.get(normalized_name, f"project:{project.id}")
            nodes.setdefault(node_id, GraphNode(id=node_id, type="project", label=project.name, metadata={"project_id": project.id}))
            project_node_by_id[project.id] = node_id
            project_node_by_label[normalized_name] = node_id
            project_node_by_label[self._normalize_label(f"{project.name} project")] = node_id

        for task in self.db.scalars(select(Task)).all():
            node_id = f"task:{task.id}"
            nodes[node_id] = GraphNode(id=node_id, type="task", label=task.title, metadata={"raw_item_id": task.source_raw_item_id})
            if task.project_id:
                project_node_id = project_node_by_id.get(task.project_id, f"project:{task.project_id}")
                edges[f"project-task:{task.project_id}:{task.id}"] = GraphEdge(
                    id=f"project-task:{task.project_id}:{task.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has task",
                    relationship_type="has_task",
                )

        for idea in self.db.scalars(select(Idea)).all():
            node_id = f"idea:{idea.id}"
            nodes[node_id] = GraphNode(id=node_id, type="idea", label=idea.body[:80], metadata={"raw_item_id": idea.source_raw_item_id})
            if idea.project_id:
                project_node_id = project_node_by_id.get(idea.project_id, f"project:{idea.project_id}")
                edges[f"project-idea:{idea.project_id}:{idea.id}"] = GraphEdge(
                    id=f"project-idea:{idea.project_id}:{idea.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has idea",
                    relationship_type="has_idea",
                )

        for decision in self.db.scalars(select(Decision)).all():
            node_id = f"decision:{decision.id}"
            nodes[node_id] = GraphNode(id=node_id, type="decision", label=decision.title, metadata={"raw_item_id": decision.source_raw_item_id})
            if decision.project_id:
                project_node_id = project_node_by_id.get(decision.project_id, f"project:{decision.project_id}")
                edges[f"project-decision:{decision.project_id}:{decision.id}"] = GraphEdge(
                    id=f"project-decision:{decision.project_id}:{decision.id}",
                    source=project_node_id,
                    target=node_id,
                    label="has decision",
                    relationship_type="has_decision",
                )

        for question in self.db.scalars(select(OpenQuestion)).all():
            node_id = f"question:{question.id}"
            nodes[node_id] = GraphNode(id=node_id, type="question", label=question.question, metadata={"raw_item_id": question.source_raw_item_id})
            if question.project_id:
                project_node_id = project_node_by_id.get(question.project_id, f"project:{question.project_id}")
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
            related_project_ids = {
                item.project_id
                for item in [*memory.tasks, *memory.ideas, *memory.open_questions, *decisions_by_memory_id.get(memory.id, [])]
                if item.project_id
            }
            related_project_node_ids = {project_node_by_id[project_id] for project_id in related_project_ids if project_id in project_node_by_id}
            fallback_source_node_id = self._source_node_id(memory.raw_item_id)

            for tag in memory.tags:
                if self._normalize_label(tag.name) in project_node_by_label:
                    continue
                tag_node_id = f"tag:{tag.id}"
                nodes.setdefault(tag_node_id, GraphNode(id=tag_node_id, type="tag", label=tag.name))

                if related_project_node_ids:
                    for project_node_id in related_project_node_ids:
                        edge_id = f"project-tag:{project_node_id}:{tag.id}"
                        edges.setdefault(
                            edge_id,
                            GraphEdge(id=edge_id, source=project_node_id, target=tag_node_id, label="tagged", relationship_type="tagged"),
                        )
                else:
                    raw_item = self.db.get(RawItem, memory.raw_item_id)
                    nodes.setdefault(
                        fallback_source_node_id,
                        GraphNode(
                            id=fallback_source_node_id,
                            type="source",
                            label=raw_item.title if raw_item else "Source note",
                            metadata={"raw_item_id": memory.raw_item_id},
                        ),
                    )
                    edge_id = f"source-tag:{memory.raw_item_id}:{tag.id}"
                    edges.setdefault(
                        edge_id,
                        GraphEdge(id=edge_id, source=fallback_source_node_id, target=tag_node_id, label="tagged", relationship_type="tagged"),
                    )

        for rel in self.db.scalars(select(Relationship)).all():
            source_id = self._node_id_for_label(rel.source_label, rel.source_node_type, project_node_by_label)
            target_id = self._node_id_for_label(rel.target_label, rel.target_node_type, project_node_by_label)
            nodes.setdefault(source_id, GraphNode(id=source_id, type=rel.source_node_type, label=rel.source_label, metadata={"raw_item_id": rel.source_raw_item_id}))
            nodes.setdefault(target_id, GraphNode(id=target_id, type=rel.target_node_type, label=rel.target_label, metadata={"raw_item_id": rel.source_raw_item_id}))
            if source_id == target_id:
                continue
            edges[f"rel:{rel.id}"] = GraphEdge(
                id=f"rel:{rel.id}",
                source=source_id,
                target=target_id,
                label=rel.relationship_type,
                relationship_type=rel.relationship_type,
            )

        return GraphResponse(nodes=list(nodes.values()), edges=list(edges.values()))

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
