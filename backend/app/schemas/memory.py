from datetime import datetime
from datetime import date

from pydantic import BaseModel, Field


class TaskOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    priority: str | None = None
    status: str
    due_date: date | None = None
    source_raw_item_id: str

    model_config = {"from_attributes": True}


class IdeaOut(BaseModel):
    id: str
    body: str
    source_raw_item_id: str

    model_config = {"from_attributes": True}


class QuestionOut(BaseModel):
    id: str
    question: str
    status: str
    source_raw_item_id: str

    model_config = {"from_attributes": True}


class MemoryOut(BaseModel):
    id: str
    raw_item_id: str
    memory_type: str
    summary: str
    confidence: float
    tags: list[str] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list)
    ideas: list[IdeaOut] = Field(default_factory=list)
    open_questions: list[QuestionOut] = Field(default_factory=list)
    created_at: datetime


class MemoryPatch(BaseModel):
    summary: str | None = None
    tags: list[str] | None = None
