from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://secondbrain:secondbrain@localhost:5432/second_brain"
    ollama_base_url: str = "http://localhost:11434"
    ollama_extraction_model: str = "qwen3:8b"
    ollama_embedding_model: str = "nomic-embed-text"
    inbox_folder: str = "../data/inbox"

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")

    @property
    def prompt_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "prompts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
