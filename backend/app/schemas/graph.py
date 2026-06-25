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


class GraphDuplicateCandidate(BaseModel):
    node_type: str
    canonical_label: str
    labels: list[str]
    node_ids: list[str]
    reason: str


class GraphRelationshipNormalization(BaseModel):
    original_type: str
    normalized_type: str
    count: int


class GraphUnassignedWorkItem(BaseModel):
    id: str
    type: str
    label: str
    memory_id: str
    source_title: str | None = None


class GraphProjectSummary(BaseModel):
    project_id: str
    name: str
    open_tasks: int
    open_questions: int
    active_ideas: int
    decisions: int
    risk_flags: list[str] = Field(default_factory=list)


class GraphInsightsResponse(BaseModel):
    duplicate_candidates: list[GraphDuplicateCandidate] = Field(default_factory=list)
    relationship_normalizations: list[GraphRelationshipNormalization] = Field(default_factory=list)
    unassigned_work_items: list[GraphUnassignedWorkItem] = Field(default_factory=list)
    project_summaries: list[GraphProjectSummary] = Field(default_factory=list)
