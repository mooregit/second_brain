from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Idea, OpenQuestion, Project, Relationship, Tag, Task
from app.models.decision import Decision
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


class GraphService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self) -> GraphResponse:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        for project in self.db.scalars(select(Project)).all():
            nodes[f"project:{project.id}"] = GraphNode(id=f"project:{project.id}", type="project", label=project.name, metadata={"project_id": project.id})

        for task in self.db.scalars(select(Task)).all():
            node_id = f"task:{task.id}"
            nodes[node_id] = GraphNode(id=node_id, type="task", label=task.title, metadata={"raw_item_id": task.source_raw_item_id})
            if task.project_id:
                edges[f"project-task:{task.project_id}:{task.id}"] = GraphEdge(
                    id=f"project-task:{task.project_id}:{task.id}",
                    source=f"project:{task.project_id}",
                    target=node_id,
                    label="has task",
                    relationship_type="has_task",
                )

        for idea in self.db.scalars(select(Idea)).all():
            node_id = f"idea:{idea.id}"
            nodes[node_id] = GraphNode(id=node_id, type="idea", label=idea.body[:80], metadata={"raw_item_id": idea.source_raw_item_id})
            if idea.project_id:
                edges[f"project-idea:{idea.project_id}:{idea.id}"] = GraphEdge(
                    id=f"project-idea:{idea.project_id}:{idea.id}",
                    source=f"project:{idea.project_id}",
                    target=node_id,
                    label="has idea",
                    relationship_type="has_idea",
                )

        for decision in self.db.scalars(select(Decision)).all():
            node_id = f"decision:{decision.id}"
            nodes[node_id] = GraphNode(id=node_id, type="decision", label=decision.title, metadata={"raw_item_id": decision.source_raw_item_id})
            if decision.project_id:
                edges[f"project-decision:{decision.project_id}:{decision.id}"] = GraphEdge(
                    id=f"project-decision:{decision.project_id}:{decision.id}",
                    source=f"project:{decision.project_id}",
                    target=node_id,
                    label="has decision",
                    relationship_type="has_decision",
                )

        for question in self.db.scalars(select(OpenQuestion)).all():
            node_id = f"question:{question.id}"
            nodes[node_id] = GraphNode(id=node_id, type="question", label=question.question, metadata={"raw_item_id": question.source_raw_item_id})
            if question.project_id:
                edges[f"project-question:{question.project_id}:{question.id}"] = GraphEdge(
                    id=f"project-question:{question.project_id}:{question.id}",
                    source=f"project:{question.project_id}",
                    target=node_id,
                    label="has question",
                    relationship_type="has_question",
                )

        for tag in self.db.scalars(select(Tag)).all():
            nodes[f"tag:{tag.id}"] = GraphNode(id=f"tag:{tag.id}", type="tag", label=tag.name)

        for rel in self.db.scalars(select(Relationship)).all():
            source_id = f"entity:{rel.source_label.lower().replace(' ', '-')}"
            target_id = f"entity:{rel.target_label.lower().replace(' ', '-')}"
            nodes.setdefault(source_id, GraphNode(id=source_id, type=rel.source_node_type, label=rel.source_label, metadata={"raw_item_id": rel.source_raw_item_id}))
            nodes.setdefault(target_id, GraphNode(id=target_id, type=rel.target_node_type, label=rel.target_label, metadata={"raw_item_id": rel.source_raw_item_id}))
            edges[f"rel:{rel.id}"] = GraphEdge(
                id=f"rel:{rel.id}",
                source=source_id,
                target=target_id,
                label=rel.relationship_type,
                relationship_type=rel.relationship_type,
            )

        return GraphResponse(nodes=list(nodes.values()), edges=list(edges.values()))

