import shlex
import subprocess
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import FileAsset, MediaArtifact, RawItem


class MediaAnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def analyze_raw_item(self, item: RawItem) -> str:
        video_assets = self.video_assets_for_item(item.id)
        if not video_assets:
            return ""

        for asset in video_assets:
            self._analyze_video_asset(item, asset)
        self.db.commit()
        return self.media_context_for_item(item.id)

    def video_assets_for_item(self, raw_item_id: str) -> list[FileAsset]:
        return list(
            self.db.scalars(
                select(FileAsset).where(
                    FileAsset.raw_item_id == raw_item_id,
                    FileAsset.mime_type.like("video/%"),
                )
            ).all()
        )

    def media_context_for_item(self, raw_item_id: str) -> str:
        assets = self.video_assets_for_item(raw_item_id)
        if not assets:
            return ""

        lines = ["Media analysis context:"]
        for asset in assets:
            lines.append(f"- Video attachment: {asset.filename} ({asset.mime_type or 'unknown type'}, {asset.size_bytes or 0} bytes)")
            artifacts = self._artifacts_for_asset(asset.id)
            for artifact in artifacts:
                label = artifact.artifact_type.replace("_", " ")
                lines.append(f"  - {label}: {artifact.status}")
                if artifact.text_content:
                    lines.append(self._indent(artifact.text_content.strip(), "    "))
                if artifact.stored_path:
                    lines.append(f"    path: {artifact.stored_path}")
                if artifact.error:
                    lines.append(f"    error: {artifact.error}")
        return "\n".join(lines).strip()

    def artifacts_for_item(self, raw_item_id: str) -> list[MediaArtifact]:
        return list(
            self.db.scalars(
                select(MediaArtifact)
                .where(MediaArtifact.raw_item_id == raw_item_id)
                .order_by(MediaArtifact.created_at.desc())
            ).all()
        )

    def _analyze_video_asset(self, item: RawItem, asset: FileAsset) -> None:
        source_path = Path(asset.stored_path)
        output_dir = self._artifact_dir(asset)
        output_dir.mkdir(parents=True, exist_ok=True)

        audio_artifact = self._extract_audio(item.id, asset, source_path, output_dir)
        self._transcribe_audio(item.id, asset, audio_artifact, output_dir)
        self._sample_frame(item.id, asset, source_path, output_dir)

    def _extract_audio(self, raw_item_id: str, asset: FileAsset, source_path: Path, output_dir: Path) -> MediaArtifact:
        artifact = self._get_or_create_artifact(raw_item_id, asset.id, "audio")
        if artifact.status == "processed" and artifact.stored_path and Path(artifact.stored_path).exists():
            return artifact

        audio_path = output_dir / "audio.wav"
        artifact.status = "processing"
        artifact.stored_path = str(audio_path)
        artifact.error = None
        artifact.metadata_json = {"command": "ffmpeg", "source_path": str(source_path)}
        try:
            self._run(["ffmpeg", "-y", "-i", str(source_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)])
            artifact.status = "processed"
        except Exception as exc:
            artifact.status = "failed"
            artifact.error = str(exc)
        return artifact

    def _transcribe_audio(self, raw_item_id: str, asset: FileAsset, audio_artifact: MediaArtifact, output_dir: Path) -> MediaArtifact:
        artifact = self._get_or_create_artifact(raw_item_id, asset.id, "transcript")
        if artifact.status == "processed" and artifact.text_content:
            return artifact

        if audio_artifact.status != "processed" or not audio_artifact.stored_path:
            artifact.status = "failed"
            artifact.error = "Audio extraction did not produce a usable audio file."
            artifact.metadata_json = {"audio_artifact_id": audio_artifact.id}
            return artifact

        backend = self.settings.media_transcription_backend.strip().lower()
        if backend in {"faster-whisper", "faster_whisper"}:
            return self._transcribe_with_faster_whisper(artifact, audio_artifact)
        if backend == "command":
            return self._transcribe_with_command(artifact, asset, audio_artifact, output_dir)

        artifact.status = "pending"
        artifact.text_content = "Transcript pending. Set MEDIA_TRANSCRIPTION_BACKEND to faster-whisper or command."
        artifact.error = None
        artifact.metadata_json = {"requires": "MEDIA_TRANSCRIPTION_BACKEND"}
        return artifact

    def _transcribe_with_faster_whisper(self, artifact: MediaArtifact, audio_artifact: MediaArtifact) -> MediaArtifact:
        artifact.status = "processing"
        artifact.error = None
        artifact.metadata_json = {
            "backend": "faster-whisper",
            "model": self.settings.media_transcription_model,
            "device": self.settings.media_transcription_device,
            "compute_type": self.settings.media_transcription_compute_type,
        }
        try:
            transcript, metadata = self._faster_whisper_transcribe(audio_artifact.stored_path or "")
            artifact.text_content = transcript or "faster-whisper completed but returned no transcript text."
            artifact.status = "processed" if transcript else "failed"
            artifact.metadata_json = {**artifact.metadata_json, **metadata}
            if not transcript:
                artifact.error = "faster-whisper returned no transcript text."
        except ImportError as exc:
            artifact.status = "failed"
            artifact.error = "faster-whisper is not installed in the backend environment."
            artifact.metadata_json = {**(artifact.metadata_json or {}), "error": str(exc)}
        except Exception as exc:
            artifact.status = "failed"
            artifact.error = str(exc)
        return artifact

    def _faster_whisper_transcribe(self, audio_path: str) -> tuple[str, dict]:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            self.settings.media_transcription_model,
            device=self.settings.media_transcription_device,
            compute_type=self.settings.media_transcription_compute_type,
        )
        segments, info = model.transcribe(audio_path)
        transcript_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        metadata = {
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
            "duration": getattr(info, "duration", None),
        }
        return " ".join(transcript_parts).strip(), metadata

    def _transcribe_with_command(self, artifact: MediaArtifact, asset: FileAsset, audio_artifact: MediaArtifact, output_dir: Path) -> MediaArtifact:
        command_template = self.settings.media_transcription_command.strip()
        if not command_template:
            artifact.status = "pending"
            artifact.text_content = "Transcript pending. Set MEDIA_TRANSCRIPTION_COMMAND to enable command transcription."
            artifact.error = None
            artifact.metadata_json = {"requires": "MEDIA_TRANSCRIPTION_COMMAND"}
            return artifact

        command = command_template.format(
            audio_path=audio_artifact.stored_path,
            video_path=asset.stored_path,
            output_dir=str(output_dir),
        )
        artifact.status = "processing"
        artifact.error = None
        artifact.metadata_json = {"command": command}
        try:
            completed = self._run(shlex.split(command))
            transcript = completed.stdout.strip() or self._read_transcript_file(output_dir)
            artifact.text_content = transcript or "Transcription command completed but returned no transcript text."
            artifact.status = "processed" if transcript else "failed"
            if not transcript:
                artifact.error = "Transcription command returned no stdout and produced no .txt transcript file."
        except Exception as exc:
            artifact.status = "failed"
            artifact.error = str(exc)
        return artifact

    def _sample_frame(self, raw_item_id: str, asset: FileAsset, source_path: Path, output_dir: Path) -> MediaArtifact:
        artifact = self._get_or_create_artifact(raw_item_id, asset.id, "frame_sample")
        if artifact.status == "processed" and artifact.stored_path and Path(artifact.stored_path).exists():
            return artifact

        frame_path = output_dir / "frame_001.jpg"
        artifact.status = "processing"
        artifact.stored_path = str(frame_path)
        artifact.error = None
        artifact.metadata_json = {"command": "ffmpeg", "source_path": str(source_path), "frame": 1}
        try:
            self._run(["ffmpeg", "-y", "-i", str(source_path), "-frames:v", "1", str(frame_path)])
            artifact.status = "processed"
            artifact.text_content = f"Sampled frame saved to {frame_path}."
        except Exception as exc:
            artifact.status = "failed"
            artifact.error = str(exc)
        return artifact

    def _get_or_create_artifact(self, raw_item_id: str, file_asset_id: str, artifact_type: str) -> MediaArtifact:
        artifact = self.db.scalar(
            select(MediaArtifact).where(
                MediaArtifact.raw_item_id == raw_item_id,
                MediaArtifact.file_asset_id == file_asset_id,
                MediaArtifact.artifact_type == artifact_type,
            )
        )
        if artifact:
            return artifact
        artifact = MediaArtifact(raw_item_id=raw_item_id, file_asset_id=file_asset_id, artifact_type=artifact_type)
        self.db.add(artifact)
        self.db.flush()
        return artifact

    def _artifacts_for_asset(self, file_asset_id: str) -> list[MediaArtifact]:
        return list(
            self.db.scalars(
                select(MediaArtifact)
                .where(MediaArtifact.file_asset_id == file_asset_id)
                .order_by(MediaArtifact.artifact_type)
            ).all()
        )

    def _artifact_dir(self, asset: FileAsset) -> Path:
        base = Path(self.settings.media_artifacts_folder).expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        return (base / asset.id).resolve()

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, check=True, text=True)

    def _read_transcript_file(self, output_dir: Path) -> str:
        transcript_files = sorted(output_dir.glob("*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not transcript_files:
            return ""
        return transcript_files[0].read_text(encoding="utf-8").strip()

    def _indent(self, value: str, prefix: str) -> str:
        return "\n".join(f"{prefix}{line}" for line in value.splitlines())
