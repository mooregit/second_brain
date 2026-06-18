import asyncio
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import FileAsset, MediaArtifact, Memory, RawItem
from app.services.extraction_service import ExtractionService
from app.services.media_analysis_service import MediaAnalysisService
from app.services.ollama_client import OllamaClient


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


def test_media_analysis_extracts_artifacts_and_transcript(db_session: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_item, asset = _video_asset(db_session, tmp_path)
    service = MediaAnalysisService(db_session)
    service.settings.media_artifacts_folder = str(tmp_path / "media")

    def fake_run(self: MediaAnalysisService, command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"artifact")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    def fake_transcribe(self: MediaAnalysisService, audio_path: str) -> tuple[str, dict]:
        return "The video says to update the dashboard.", {"language": "en", "duration": 3.5}

    monkeypatch.setattr(MediaAnalysisService, "_run", fake_run)
    monkeypatch.setattr(MediaAnalysisService, "_faster_whisper_transcribe", fake_transcribe)

    context = service.analyze_raw_item(raw_item)

    artifacts = db_session.scalars(select(MediaArtifact).where(MediaArtifact.file_asset_id == asset.id)).all()
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    assert by_type["audio"].status == "processed"
    assert by_type["transcript"].status == "processed"
    assert by_type["transcript"].text_content == "The video says to update the dashboard."
    assert by_type["transcript"].metadata_json["backend"] == "faster-whisper"
    assert by_type["transcript"].metadata_json["language"] == "en"
    assert by_type["frame_sample"].status == "processed"
    assert "The video says to update the dashboard." in context
    assert Path(by_type["audio"].stored_path).exists()
    assert Path(by_type["frame_sample"].stored_path).exists()


def test_media_analysis_supports_command_transcription_backend(db_session: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_item, asset = _video_asset(db_session, tmp_path)
    service = MediaAnalysisService(db_session)
    service.settings.media_artifacts_folder = str(tmp_path / "media")
    service.settings.media_transcription_backend = "command"
    service.settings.media_transcription_command = "transcribe {audio_path}"

    def fake_run(self: MediaAnalysisService, command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"artifact")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="Command transcript.", stderr="")

    monkeypatch.setattr(MediaAnalysisService, "_run", fake_run)

    service.analyze_raw_item(raw_item)

    transcript = db_session.scalar(
        select(MediaArtifact).where(MediaArtifact.file_asset_id == asset.id, MediaArtifact.artifact_type == "transcript")
    )
    assert transcript is not None
    assert transcript.status == "processed"
    assert transcript.text_content == "Command transcript."
    assert transcript.metadata_json["command"].startswith("transcribe ")


def test_extraction_prompt_includes_media_context(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_item = RawItem(source_type="gmail", title="Video email", body_text="Please inspect the attached video.")
    db_session.add(raw_item)
    db_session.commit()
    captured = {}

    async def fake_generate(self: OllamaClient, model: str, prompt: str) -> str:
        captured["prompt"] = prompt
        return """
        {
          "summary": "Video asks for a dashboard update.",
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
          "confidence": 0.9
        }
        """

    async def fake_embed_records(self: ExtractionService, memory: Memory) -> None:
        return None

    monkeypatch.setattr(OllamaClient, "generate", fake_generate)
    monkeypatch.setattr(ExtractionService, "_embed_records", fake_embed_records)
    monkeypatch.setattr(MediaAnalysisService, "analyze_raw_item", lambda self, item: "Transcript: update the dashboard.")

    memory = asyncio.run(ExtractionService(db_session).process_item(raw_item))

    assert memory.summary == "Video asks for a dashboard update."
    assert "--- Media Analysis ---" in captured["prompt"]
    assert "Transcript: update the dashboard." in captured["prompt"]


def _video_asset(db_session: Session, tmp_path) -> tuple[RawItem, FileAsset]:
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"video")
    raw_item = RawItem(source_type="gmail", title="Video", body_text="Body")
    db_session.add(raw_item)
    db_session.flush()
    asset = FileAsset(
        raw_item_id=raw_item.id,
        filename="source.mp4",
        stored_path=str(source_path),
        mime_type="video/mp4",
        size_bytes=source_path.stat().st_size,
        sha256="hash",
    )
    db_session.add(asset)
    db_session.commit()
    return raw_item, asset
