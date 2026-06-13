from fastapi import APIRouter

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/sync")
def sync_gmail() -> dict:
    return {"status": "deferred", "detail": "Gmail sync is planned after the local manual-note loop."}


@router.post("/draft-reply")
def draft_reply() -> dict:
    return {"status": "deferred", "detail": "Draft replies are planned and will never auto-send in the MVP."}

