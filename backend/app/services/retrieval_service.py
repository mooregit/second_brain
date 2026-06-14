import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, Embedding, Idea, Memory, OpenQuestion, RawItem, Task
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_service = EmbeddingService(db)

    async def retrieve(self, question: str, limit: int = 6) -> list[dict]:
        query_vector = await self.embedding_service.embed_query(question)
        scored = []
        for embedding in self.db.scalars(select(Embedding)).all():
            score = self._cosine(query_vector, embedding.vector_json)
            scored.append((score, embedding))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [self._hydrate(score, embedding) for score, embedding in scored[:limit] if score > 0]

    def _hydrate(self, score: float, embedding: Embedding) -> dict:
        title = embedding.owner_type
        text = ""
        raw_item_id = None
        if embedding.owner_type == "memory":
            item = self.db.get(Memory, embedding.owner_id)
            if item:
                title = item.summary[:80]
                text = item.summary
                raw_item_id = item.raw_item_id
        elif embedding.owner_type == "task":
            item = self.db.get(Task, embedding.owner_id)
            if item:
                title = item.title
                text = f"Task: {item.title}\n{item.description or ''}\nStatus: {item.status}"
                raw_item_id = item.source_raw_item_id
        elif embedding.owner_type == "idea":
            item = self.db.get(Idea, embedding.owner_id)
            if item:
                title = item.body[:80]
                text = f"Idea: {item.body}\nStatus: {item.status}"
                raw_item_id = item.source_raw_item_id
        elif embedding.owner_type == "decision":
            item = self.db.get(Decision, embedding.owner_id)
            if item:
                title = item.title
                text = f"Decision: {item.title}\nRationale: {item.rationale or ''}\nConfidence: {item.confidence}"
                raw_item_id = item.source_raw_item_id
        elif embedding.owner_type == "open_question":
            item = self.db.get(OpenQuestion, embedding.owner_id)
            if item:
                title = item.question[:80]
                text = f"Open question: {item.question}\nStatus: {item.status}"
                raw_item_id = item.source_raw_item_id
        source_title = title
        if raw_item_id:
            raw = self.db.get(RawItem, raw_item_id)
            if raw:
                source_title = raw.title
        return {
            "owner_type": embedding.owner_type,
            "owner_id": embedding.owner_id,
            "score": score,
            "title": source_title,
            "text": text,
            "raw_item_id": raw_item_id,
        }

    def _cosine(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)
