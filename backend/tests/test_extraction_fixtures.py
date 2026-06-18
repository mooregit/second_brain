import json
from pathlib import Path

from app.schemas.extraction import ExtractionResult


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "extraction"


def test_betright_extraction_fixture_matches_expected_shape() -> None:
    note = (FIXTURE_DIR / "betright_note.txt").read_text(encoding="utf-8")
    payload = json.loads((FIXTURE_DIR / "betright_expected.json").read_text(encoding="utf-8"))

    result = ExtractionResult.model_validate(payload)

    assert "BetRight" in note
    assert result.projects == ["BetRight"]
    assert [task.title for task in result.tasks] == [
        "Add injury classification for BetRight",
        "Check whether injury classification affects player prop projections",
    ]
    assert result.ideas == ["Use a local LLM to categorize ESPN injury blurbs"]
    assert result.open_questions == ["Should injury status directly adjust player prop projections?"]
    assert {"BetRight", "injuries", "local-llm"}.issubset(set(result.tags))
    assert any(
        relationship.source == "injury classification"
        and relationship.target == "player prop projections"
        and relationship.relationship == "may_affect"
        for relationship in result.relationships
    )
