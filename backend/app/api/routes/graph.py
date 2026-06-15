from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.graph import GraphResponse
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
def graph(show_archived: bool = False, db: Session = Depends(get_db)) -> GraphResponse:
    return GraphService(db).build(show_archived=show_archived)
