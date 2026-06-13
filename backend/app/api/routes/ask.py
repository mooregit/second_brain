from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ask import AskRequest, AskResponse
from app.services.ask_service import AskService

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
async def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    try:
        return await AskService(db).ask(payload.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

