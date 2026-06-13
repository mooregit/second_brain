import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Embedding
from app.services.ollama_client import OllamaClient


class EmbeddingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.ollama = OllamaClient()

    async def embed_owner(self, owner_type: str, owner_id: str, text: str) -> Embedding:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = self.db.scalar(
            select(Embedding).where(
                Embedding.owner_type == owner_type,
                Embedding.owner_id == owner_id,
                Embedding.text_hash == text_hash,
                Embedding.model == self.settings.ollama_embedding_model,
            )
        )
        if existing:
            return existing
        vector = await self.ollama.embed(self.settings.ollama_embedding_model, text)
        embedding = Embedding(owner_type=owner_type, owner_id=owner_id, model=self.settings.ollama_embedding_model, vector_json=vector, text_hash=text_hash)
        self.db.add(embedding)
        self.db.commit()
        return embedding

    async def embed_query(self, text: str) -> list[float]:
        return await self.ollama.embed(self.settings.ollama_embedding_model, text)

