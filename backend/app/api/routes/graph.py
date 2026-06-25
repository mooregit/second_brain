from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Decision, Idea, Memory, OpenQuestion, Project, RawItem, Relationship, Tag, Task
from app.schemas.graph import GraphInsightsResponse, GraphResponse
from app.services.graph_insights_service import GraphInsightsService
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


class TagRename(BaseModel):
    name: str = Field(min_length=1)


class LabelRename(BaseModel):
    node_type: str = Field(pattern="^(entity|person)$")
    old_label: str = Field(min_length=1)
    new_label: str = Field(min_length=1)


class LabelDelete(BaseModel):
    node_type: str = Field(pattern="^(entity|person)$")
    label: str = Field(min_length=1)


class ManualRelationshipCreate(BaseModel):
    source_label: str = Field(min_length=1)
    source_node_type: str = Field(min_length=1)
    target_label: str = Field(min_length=1)
    target_node_type: str = Field(min_length=1)
    relationship_type: str = Field(default="related_to", min_length=1)


@router.get("", response_model=GraphResponse)
def graph(show_archived: bool = False, db: Session = Depends(get_db)) -> GraphResponse:
    return GraphService(db).build(show_archived=show_archived)


@router.get("/insights", response_model=GraphInsightsResponse)
def graph_insights(show_archived: bool = False, db: Session = Depends(get_db)) -> GraphInsightsResponse:
    return GraphInsightsService(db).build(show_archived=show_archived)


@router.post("/relationships")
def create_manual_relationship(payload: ManualRelationshipCreate, db: Session = Depends(get_db)) -> dict:
    source_label = payload.source_label.strip()
    target_label = payload.target_label.strip()
    relationship_type = payload.relationship_type.strip() or "related_to"
    if not source_label or not target_label:
        raise HTTPException(status_code=422, detail="Source and target labels are required")

    raw_item = RawItem(
        source_type="manual",
        title=f"Manual graph relationship: {source_label} {relationship_type} {target_label}"[:160],
        body_text=f"Manual graph relationship: {source_label} {relationship_type} {target_label}",
        status="processed",
        metadata_json={"source": "manual_graph_relationship"},
    )
    db.add(raw_item)
    db.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary=raw_item.body_text,
        confidence=1.0,
        validated_json={
            "summary": raw_item.body_text,
            "memory_type": "note",
            "projects": [],
            "people": [],
            "tasks": [],
            "ideas": [],
            "decisions": [],
            "open_questions": [],
            "tags": ["manual-graph"],
            "entities": [source_label, target_label],
            "relationships": [
                {
                    "source": source_label,
                    "target": target_label,
                    "relationship": relationship_type,
                }
            ],
            "suggested_actions": [],
            "confidence": 1.0,
        },
        raw_llm_output="manual graph relationship",
    )
    db.add(memory)
    db.flush()
    relationship = Relationship(
        memory_id=memory.id,
        source_label=source_label,
        target_label=target_label,
        relationship_type=relationship_type,
        source_node_type=payload.source_node_type.strip() or "entity",
        target_node_type=payload.target_node_type.strip() or "entity",
        source_raw_item_id=raw_item.id,
    )
    db.add(relationship)
    db.commit()
    return {"status": "created", "id": relationship.id, "raw_item_id": raw_item.id, "memory_id": memory.id}


@router.post("/deduplicate")
def deduplicate_graph(db: Session = Depends(get_db)) -> dict:
    result = {
        "projects_merged": 0,
        "tags_merged": 0,
        "relationship_labels_normalized": 0,
        "relationship_node_types_updated": 0,
        "relationships_removed": 0,
    }
    result["projects_merged"] = _merge_duplicate_projects(db)
    result["tags_merged"] = _merge_duplicate_tags(db)
    result["relationship_labels_normalized"] = _normalize_relationship_labels(db)
    result["relationship_node_types_updated"] = _canonicalize_relationship_node_types(db)
    result["relationships_removed"] = _remove_duplicate_relationships(db)
    db.commit()
    result["status"] = "deduplicated"
    return result


@router.post("/relationships/normalize")
def normalize_relationships(db: Session = Depends(get_db)) -> dict:
    updated = 0
    for relationship in db.scalars(select(Relationship)).all():
        normalized = GraphInsightsService.normalize_relationship_type(relationship.relationship_type)
        if relationship.relationship_type != normalized:
            relationship.relationship_type = normalized
            updated += 1
    db.commit()
    return {"status": "normalized", "updated": updated}


@router.patch("/tags/{tag_id}")
def rename_tag(tag_id: str, payload: TagRename, db: Session = Depends(get_db)) -> dict:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    new_name = payload.name.strip()
    if not new_name:
        raise HTTPException(status_code=422, detail="Tag name is required")

    existing = db.scalar(select(Tag).where(Tag.name == new_name, Tag.id != tag_id))
    if existing:
        for memory in list(tag.memories):
            if existing not in memory.tags:
                memory.tags.append(existing)
            memory.tags.remove(tag)
        db.delete(tag)
        db.commit()
        return {"status": "merged", "id": existing.id, "name": existing.name}

    tag.name = new_name
    db.commit()
    db.refresh(tag)
    return {"status": "renamed", "id": tag.id, "name": tag.name}


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: str, db: Session = Depends(get_db)) -> dict:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    for memory in list(tag.memories):
        memory.tags.remove(tag)
    db.delete(tag)
    db.commit()
    return {"status": "deleted", "id": tag_id}


@router.patch("/labels")
def rename_label(payload: LabelRename, db: Session = Depends(get_db)) -> dict:
    old_label = payload.old_label.strip()
    new_label = payload.new_label.strip()
    if not old_label or not new_label:
        raise HTTPException(status_code=422, detail="Labels are required")

    updated = 0
    for relationship in db.scalars(select(Relationship)).all():
        if relationship.source_node_type == payload.node_type and _normalize_label(relationship.source_label) == _normalize_label(old_label):
            relationship.source_label = new_label
            updated += 1
        if relationship.target_node_type == payload.node_type and _normalize_label(relationship.target_label) == _normalize_label(old_label):
            relationship.target_label = new_label
            updated += 1
    db.commit()
    return {"status": "renamed", "node_type": payload.node_type, "old_label": old_label, "new_label": new_label, "updated": updated}


@router.api_route("/labels", methods=["DELETE"])
def delete_label(payload: LabelDelete, db: Session = Depends(get_db)) -> dict:
    label = payload.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="Label is required")

    deleted = 0
    for relationship in db.scalars(select(Relationship)).all():
        source_matches = relationship.source_node_type == payload.node_type and _normalize_label(relationship.source_label) == _normalize_label(label)
        target_matches = relationship.target_node_type == payload.node_type and _normalize_label(relationship.target_label) == _normalize_label(label)
        if source_matches or target_matches:
            db.delete(relationship)
            deleted += 1
    db.commit()
    return {"status": "deleted", "node_type": payload.node_type, "label": label, "deleted": deleted}


def _normalize_label(label: str) -> str:
    normalized = " ".join(label.lower().strip().split())
    normalized = normalized.rstrip("/")
    if normalized.endswith(" project"):
        normalized = normalized.removesuffix(" project").strip()
    return normalized


def _canonical_label(label: str) -> str:
    return " ".join(label.strip().split()).rstrip("/")


def _merge_duplicate_projects(db: Session) -> int:
    merged = 0
    groups: dict[str, list[Project]] = {}
    for project in db.scalars(select(Project)).all():
        groups.setdefault(_normalize_label(project.name), []).append(project)

    for projects in groups.values():
        if len(projects) < 2:
            continue
        projects.sort(key=lambda project: (_normalize_label(project.name) != _canonical_label(project.name).lower(), project.created_at, project.name.lower()))
        canonical = projects[0]
        for duplicate in projects[1:]:
            for model in (Task, Idea, Decision, OpenQuestion):
                for record in db.scalars(select(model).where(model.project_id == duplicate.id)).all():
                    record.project_id = canonical.id
                    record.project = canonical
            if not canonical.description and duplicate.description:
                canonical.description = duplicate.description
            for relationship in db.scalars(select(Relationship)).all():
                if relationship.source_node_type == "project" and _normalize_label(relationship.source_label) == _normalize_label(duplicate.name):
                    relationship.source_label = canonical.name
                if relationship.target_node_type == "project" and _normalize_label(relationship.target_label) == _normalize_label(duplicate.name):
                    relationship.target_label = canonical.name
            db.delete(duplicate)
            merged += 1
    return merged


def _merge_duplicate_tags(db: Session) -> int:
    merged = 0
    groups: dict[str, list[Tag]] = {}
    for tag in db.scalars(select(Tag)).all():
        groups.setdefault(_normalize_label(tag.name), []).append(tag)

    for tags in groups.values():
        if len(tags) < 2:
            continue
        tags.sort(key=lambda tag: (_canonical_label(tag.name) != tag.name, tag.name.lower()))
        canonical = tags[0]
        for duplicate in tags[1:]:
            for memory in list(duplicate.memories):
                if canonical not in memory.tags:
                    memory.tags.append(canonical)
                memory.tags.remove(duplicate)
            db.delete(duplicate)
            merged += 1
    return merged


def _normalize_relationship_labels(db: Session) -> int:
    updated = 0
    canonical_labels = {label: canonical for label, (_node_type, canonical) in _existing_work_labels(db).items()}
    for relationship in db.scalars(select(Relationship)).all():
        source_label = canonical_labels.get(_normalize_label(relationship.source_label), _canonical_label(relationship.source_label))
        target_label = canonical_labels.get(_normalize_label(relationship.target_label), _canonical_label(relationship.target_label))
        relationship_type = _canonical_label(relationship.relationship_type).lower().replace(" ", "_")
        if source_label != relationship.source_label:
            relationship.source_label = source_label
            updated += 1
        if target_label != relationship.target_label:
            relationship.target_label = target_label
            updated += 1
        if relationship_type != relationship.relationship_type:
            relationship.relationship_type = relationship_type
            updated += 1
    return updated


def _canonicalize_relationship_node_types(db: Session) -> int:
    label_types = {label: node_type for label, (node_type, _canonical) in _existing_work_labels(db).items()}
    updated = 0
    for relationship in db.scalars(select(Relationship)).all():
        source_type = label_types.get(_normalize_label(relationship.source_label))
        target_type = label_types.get(_normalize_label(relationship.target_label))
        if source_type and relationship.source_node_type not in {source_type, "project"}:
            relationship.source_node_type = source_type
            updated += 1
        if target_type and relationship.target_node_type not in {target_type, "project"}:
            relationship.target_node_type = target_type
            updated += 1
    return updated


def _existing_work_labels(db: Session) -> dict[str, tuple[str, str]]:
    label_types: dict[str, tuple[str, str]] = {}
    for project in db.scalars(select(Project)).all():
        label_types.setdefault(_normalize_label(project.name), ("project", project.name))
    for task in db.scalars(select(Task)).all():
        label_types.setdefault(_normalize_label(task.title), ("task", task.title))
    for idea in db.scalars(select(Idea)).all():
        label_types.setdefault(_normalize_label(idea.body), ("idea", idea.body))
    for question in db.scalars(select(OpenQuestion)).all():
        label_types.setdefault(_normalize_label(question.question), ("question", question.question))
    for decision in db.scalars(select(Decision)).all():
        label_types.setdefault(_normalize_label(decision.title), ("decision", decision.title))
    return label_types


def _remove_duplicate_relationships(db: Session) -> int:
    removed = 0
    seen: set[tuple[str, str, str, str, str]] = set()
    relationships = sorted(db.scalars(select(Relationship)).all(), key=lambda relationship: relationship.created_at)
    for relationship in relationships:
        key = (
            relationship.source_node_type,
            _normalize_label(relationship.source_label),
            relationship.target_node_type,
            _normalize_label(relationship.target_label),
            _normalize_label(relationship.relationship_type),
        )
        if key in seen:
            db.delete(relationship)
            removed += 1
            continue
        seen.add(key)
    return removed
