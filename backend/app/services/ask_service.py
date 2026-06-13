from app.core.config import get_settings
from app.schemas.ask import AskResponse, AskSource
from app.services.ollama_client import OllamaClient
from app.services.retrieval_service import RetrievalService


class AskService:
    def __init__(self, db) -> None:
        self.db = db
        self.settings = get_settings()
        self.ollama = OllamaClient()
        self.retrieval = RetrievalService(db)

    async def ask(self, question: str) -> AskResponse:
        matches = await self.retrieval.retrieve(question)
        if not matches:
            return AskResponse(answer="There is not enough stored context to answer that yet.", sources=[])
        context = "\n\n".join(
            f"Source {idx + 1} ({match['owner_type']} {match['owner_id']} from raw item {match['raw_item_id']}):\n{match['text']}"
            for idx, match in enumerate(matches)
        )
        prompt = self._prompt("ask.md").replace("{{question}}", question).replace("{{context}}", context)
        answer = await self.ollama.generate(self.settings.ollama_extraction_model, prompt)
        return AskResponse(
            answer=answer.strip(),
            sources=[
                AskSource(
                    owner_type=match["owner_type"],
                    owner_id=match["owner_id"],
                    score=match["score"],
                    title=match["title"],
                    raw_item_id=match["raw_item_id"],
                )
                for match in matches
            ],
        )

    def _prompt(self, filename: str) -> str:
        return (self.settings.prompt_dir / filename).read_text(encoding="utf-8")

