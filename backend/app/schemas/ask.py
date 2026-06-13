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
    answer: str
    sources: list[AskSource]

