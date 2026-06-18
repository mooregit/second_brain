from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import EmailMessage, Person, RawItem
from app.schemas.extraction import ExtractionResult
from app.services.extraction_service import ExtractionService


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


def test_persist_result_upserts_people_by_normalized_name(db_session: Session) -> None:
    first_item = RawItem(source_type="manual", title="First", body_text="Talk to Ada Lovelace.")
    second_item = RawItem(source_type="manual", title="Second", body_text="Follow up with ada lovelace.")
    db_session.add_all([first_item, second_item])
    db_session.commit()

    service = ExtractionService(db_session)
    service._persist_result(first_item, _result(["Ada Lovelace"]), "{}")
    service._persist_result(second_item, _result(["ada   lovelace"]), "{}")
    db_session.commit()

    people = db_session.scalars(select(Person)).all()
    assert len(people) == 1
    assert people[0].name == "Ada Lovelace"


def test_persist_result_does_not_create_person_for_gmail_sender_signature(db_session: Session) -> None:
    item = RawItem(source_type="gmail", title="Website needs work", body_text="https://example.com\n\nRussell G. Moore")
    db_session.add(item)
    db_session.flush()
    db_session.add(
        EmailMessage(
            raw_item_id=item.id,
            gmail_message_id="gmail-person-ignore",
            from_email="russell@example.com",
            subject="Website needs work",
        )
    )
    db_session.commit()

    ExtractionService(db_session)._persist_result(item, _result(["Russell G. Moore"]), "{}")
    db_session.commit()

    assert db_session.scalars(select(Person)).all() == []


def test_normalize_extraction_payload_adds_required_fields_and_coerces_task_strings(db_session: Session) -> None:
    payload = {
        "title": "A Builder You Should Know",
        "tasks": [
            "Build a marketplace for Armenia",
            "Give Epic away to teachers to drive organic growth",
        ],
        "tags": ["startup"],
    }

    normalized = ExtractionService(db_session)._normalize_extraction_payload(payload, "Email subject")
    result = ExtractionResult.model_validate(normalized)

    assert result.summary == "A Builder You Should Know"
    assert result.confidence == 0.5
    assert [task.title for task in result.tasks] == [
        "Build a marketplace for Armenia",
        "Give Epic away to teachers to drive organic growth",
    ]
    assert all(task.status == "open" for task in result.tasks)


def test_normalize_extraction_payload_summarizes_alternate_list_shape(db_session: Session) -> None:
    payload = {
        "key_ai_trends": [
            {"title": "Agentic workflows"},
            {"title": "Local models"},
        ],
        "relationships": [{"from": "agents", "to": "workflows", "type": "automate"}],
    }

    normalized = ExtractionService(db_session)._normalize_extraction_payload(payload, "AI trends email")
    result = ExtractionResult.model_validate(normalized)

    assert result.summary == "Agentic workflows; Local models"
    assert result.relationships[0].source == "agents"
    assert result.relationships[0].target == "workflows"
    assert result.relationships[0].relationship == "automate"


def _result(people: list[str]) -> ExtractionResult:
    return ExtractionResult.model_validate(
        {
            "summary": "Summary",
            "memory_type": "note",
            "projects": [],
            "people": people,
            "tasks": [],
            "ideas": [],
            "decisions": [],
            "open_questions": [],
            "tags": [],
            "entities": [],
            "relationships": [],
            "suggested_actions": [],
            "confidence": 0.8,
        }
    )
