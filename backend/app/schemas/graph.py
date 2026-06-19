from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    metadata: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relationship_type: str
    origin: str = "relationship"
    confidence: float | None = None


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
