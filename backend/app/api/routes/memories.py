from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Memory, Tag
from app.schemas.memory import MemoryOut, MemoryPatch

router = APIRouter(prefix="/memories", tags=["memories"])


def memory_out(memory: Memory) -> MemoryOut:
    return MemoryOut(
        id=memory.id,
        raw_item_id=memory.raw_item_id,
        memory_type=memory.memory_type,
        summary=memory.summary,
        confidence=memory.confidence,
        tags=[tag.name for tag in memory.tags],
        tasks=memory.tasks,
        ideas=memory.ideas,
        open_questions=memory.open_questions,
        created_at=memory.created_at,
    )


@router.get("", response_model=list[MemoryOut])
def list_memories(db: Session = Depends(get_db)) -> list[MemoryOut]:
    memories = db.scalars(
        select(Memory)
        .options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.open_questions))
        .order_by(Memory.created_at.desc())
    ).all()
    return [memory_out(memory) for memory in memories]


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: str, db: Session = Depends(get_db)) -> MemoryOut:
    memory = db.scalars(
        select(Memory)
        .where(Memory.id == memory_id)
        .options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.open_questions))
    ).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory_out(memory)


@router.patch("/{memory_id}", response_model=MemoryOut)
def patch_memory(memory_id: str, payload: MemoryPatch, db: Session = Depends(get_db)) -> MemoryOut:
    memory = db.scalars(
        select(Memory)
        .where(Memory.id == memory_id)
        .options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.open_questions))
    ).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if payload.summary is not None:
        memory.summary = payload.summary
    if payload.tags is not None:
        tags: list[Tag] = []
        for name in payload.tags:
            normalized = name.strip()
            if not normalized:
                continue
            tag = db.scalar(select(Tag).where(Tag.name == normalized)) or Tag(name=normalized)
            db.add(tag)
            tags.append(tag)
        memory.tags = tags
    db.commit()
    db.refresh(memory)
    return memory_out(memory)

