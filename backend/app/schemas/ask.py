from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskSource(BaseModel):
    owner_type: str
    owner_id: str
    score: float
    title: str
    raw_item_id: str | None = None


class AskResponse(BaseModel):
    ask_run_id: str | None = None
    answer: str
    sources: list[AskSource]


class AskSaveRequest(BaseModel):
    save_as: Literal["task", "open_question", "decision"]
    title: str | None = None
    body: str | None = None
    rationale: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)


class AskSaveResponse(BaseModel):
    raw_item_id: str
    memory_id: str
    entity_type: str
    entity_id: str
