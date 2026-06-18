from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Memory, RawItem, Relationship, Tag
from app.schemas.graph import GraphResponse
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
    return " ".join(label.lower().strip().split())
