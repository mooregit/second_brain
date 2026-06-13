from typing import Literal

from pydantic import BaseModel, Field


class ExtractedTask(BaseModel):
    title: str
    description: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: str | None = None
    status: str = "open"


class ExtractedDecision(BaseModel):
    title: str
    rationale: str | None = None
    confidence: float = Field(ge=0, le=1)


class ExtractedRelationship(BaseModel):
    source: str
    target: str
    relationship: str


class ExtractionResult(BaseModel):
    summary: str
    memory_type: Literal["note", "task", "idea", "decision", "question", "resource", "email", "file"] = "note"
    projects: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    tasks: list[ExtractedTask] = Field(default_factory=list)
    ideas: list[str] = Field(default_factory=list)
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

