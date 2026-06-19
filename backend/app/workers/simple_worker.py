import asyncio

from app.core.database import SessionLocal
from app.services.gmail_poller import GmailPoller


def run_once() -> dict:
    return asyncio.run(GmailPoller(SessionLocal).poll_once())
