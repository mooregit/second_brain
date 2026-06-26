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


def test_enrich_sparse_knowledge_result_extracts_topics_from_glossary_summary(db_session: Session) -> None:
    item = RawItem(source_type="upload", title="study-guide.pdf", body_text="")
    result = ExtractionResult.model_validate(
        {
            "summary": """
### **Algorithms & Data Structures**
- **Selection Sort**: Finds the minimum element repeatedly.
- **Binary Search**: Divides a sorted array in half repeatedly.

### **Machine Learning**
- **Supervised Learning**: Learning from labeled data.
- **Neural Networks**: Models used for pattern recognition.
""",
            "memory_type": "note",
            "projects": [],
            "people": [],
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

    enriched = ExtractionService(db_session)._enrich_sparse_knowledge_result(item, result)

    assert enriched.memory_type == "resource"
    assert enriched.tags == ["Algorithms & Data Structures", "Machine Learning"]
    assert "Selection Sort" in enriched.entities
    assert "Neural Networks" in enriched.entities
    assert {relationship.source for relationship in enriched.relationships} == {"Algorithms & Data Structures", "Machine Learning"}
    assert any(relationship.target == "Binary Search" and relationship.relationship == "includes" for relationship in enriched.relationships)


def test_parse_extraction_output_recovers_missing_commas_between_objects(db_session: Session) -> None:
    malformed = """
{
  "summary": "Chunk about algorithm tradeoffs.",
  "memory_type": "resource",
  "projects": [],
  "people": [],
  "tasks": [],
  "ideas": [],
  "decisions": [],
  "open_questions": [],
  "tags": ["algorithms", "sorting"],
  "entities": ["Selection Sort", "Merge Sort"],
  "relationships": [
    {"source": "sorting", "target": "Selection Sort", "relationship": "includes"}
    {"source": "sorting", "target": "Merge Sort", "relationship": "includes"}
  ],
  "suggested_actions": [],
  "confidence": 0.74
}
"""

    parsed = ExtractionService(db_session)._parse_extraction_output(malformed)
    result = ExtractionResult.model_validate(ExtractionService(db_session)._normalize_extraction_payload(parsed, "Chunk"))

    assert result.summary == "Chunk about algorithm tradeoffs."
    assert result.tags == ["algorithms", "sorting"]
    assert [relationship.target for relationship in result.relationships] == ["Selection Sort", "Merge Sort"]


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
