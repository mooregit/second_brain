from datetime import datetime

from pydantic import BaseModel


class ManualItemCreate(BaseModel):
    title: str | None = None
    body_text: str


class RawItemOut(BaseModel):
    id: str
    source_type: str
    title: str
    body_text: str
    content_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

