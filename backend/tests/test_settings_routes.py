import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.settings import SettingsPatch, list_ollama_models, patch_settings
from app.core.database import Base
from app.services.ollama_client import OllamaClient
from app.services.settings_service import SettingsService


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


def test_patch_settings_persists_ollama_model_selection(db_session: Session) -> None:
    result = patch_settings(
        SettingsPatch(ollama_extraction_model="qwen3:14b", ollama_embedding_model="nomic-embed-text"),
        db_session,
    )

    service = SettingsService(db_session)
    assert result["ollama_extraction_model"] == "qwen3:14b"
    assert result["ollama_embedding_model"] == "nomic-embed-text"
    assert service.get_ollama_extraction_model() == "qwen3:14b"
    assert service.get_ollama_embedding_model() == "nomic-embed-text"


def test_ollama_model_listing_identifies_completion_and_embedding_models(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_list_models(self: OllamaClient) -> list[dict]:
        return [
            {"name": "qwen3:8b", "supports_completion": True, "supports_embedding": False},
            {"name": "nomic-embed-text:latest", "supports_completion": False, "supports_embedding": True},
        ]

    monkeypatch.setattr(OllamaClient, "list_models", fake_list_models)

    result = asyncio.run(list_ollama_models())

    assert [model["name"] for model in result["completion_models"]] == ["qwen3:8b"]
    assert [model["name"] for model in result["embedding_models"]] == ["nomic-embed-text:latest"]
