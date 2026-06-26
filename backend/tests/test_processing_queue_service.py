import asyncio
from collections.abc import Generator
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import ProcessingRun, RawItem
from app.services.extraction_service import ExtractionService
from app.services.processing_queue_service import ProcessingQueueService


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_enqueue_item_creates_pending_run_and_prevents_duplicate_active_runs(db_session: Session) -> None:
    item = _item(db_session)
    service = ProcessingQueueService(db_session)

    first = service.enqueue_item(item.id)
    second = service.enqueue_item(item.id)

    assert first.id == second.id
    assert first.status == "pending"
    assert db_session.get(RawItem, item.id).status == "pending"
    assert len(db_session.scalars(select(ProcessingRun)).all()) == 1


def test_cancel_pending_run_marks_item_new(db_session: Session) -> None:
    item = _item(db_session)
    service = ProcessingQueueService(db_session)
    run = service.enqueue_item(item.id)

    canceled = service.cancel_run(run.id)

    assert canceled.status == "canceled"
    assert canceled.finished_at is not None
    assert db_session.get(RawItem, item.id).status == "new"


def test_retry_run_creates_new_pending_run(db_session: Session) -> None:
    item = _item(db_session)
    service = ProcessingQueueService(db_session)
    run = service.enqueue_item(item.id)
    run.status = "failed"
    db_session.commit()

    retry = service.retry_run(run.id)

    assert retry.id != run.id
    assert retry.status == "pending"
    assert retry.raw_item_id == item.id
    assert len(db_session.scalars(select(ProcessingRun)).all()) == 2


def test_process_pending_uses_extraction_service_run(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    item = _item(db_session)
    service = ProcessingQueueService(db_session)
    run = service.enqueue_item(item.id)

    async def fake_process_item(self: ExtractionService, raw_item: RawItem, run: ProcessingRun | None = None):
        assert run is not None
        raw_item.status = "processed"
        run.status = "succeeded"
        db_session.commit()
        return None

    monkeypatch.setattr(ExtractionService, "process_item", fake_process_item)

    processed = asyncio.run(service.process_pending(limit=3))

    assert [item.id for item in processed] == [run.id]
    assert db_session.get(ProcessingRun, run.id).status == "succeeded"
    assert db_session.get(RawItem, item.id).status == "processed"


def test_requeue_stale_processing_marks_run_pending(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    class QueueSettings:
        processing_stale_minutes = 60

    item = _item(db_session)
    service = ProcessingQueueService(db_session)
    run = service.enqueue_item(item.id)
    run.status = "processing"
    run.started_at = datetime.utcnow() - timedelta(hours=2)
    item.status = "processing"
    db_session.commit()
    monkeypatch.setattr("app.services.processing_queue_service.get_settings", lambda: QueueSettings())

    stale_runs = service.requeue_stale_processing()

    assert [stale.id for stale in stale_runs] == [run.id]
    assert db_session.get(ProcessingRun, run.id).status == "pending"
    assert db_session.get(RawItem, item.id).status == "pending"


def _item(db_session: Session) -> RawItem:
    item = RawItem(source_type="manual", title="Queue me", body_text="Queue body")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item
