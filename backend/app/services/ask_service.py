from app.core.config import get_settings
from app.schemas.ask import AskResponse, AskSource
from app.models import AskRun
from app.services.ollama_client import OllamaClient
from app.services.retrieval_service import RetrievalService
from app.services.settings_service import SettingsService


class AskService:
    def __init__(self, db) -> None:
        self.db = db
        self.settings = get_settings()
        self.app_settings = SettingsService(db)
        self.ollama = OllamaClient()
        self.retrieval = RetrievalService(db)

    async def ask(self, question: str) -> AskResponse:
        matches = await self.retrieval.retrieve(question)
        if not matches:
            response = AskResponse(answer="There is not enough stored context to answer that yet.", sources=[])
            ask_run = self._store_run(question, response)
            response.ask_run_id = ask_run.id
            return response
        context = "\n\n".join(
            f"Source {idx + 1} ({match['owner_type']} {match['owner_id']} from raw item {match['raw_item_id']}):\n{match['text']}"
            for idx, match in enumerate(matches)
        )
        prompt = self._prompt("ask.md").replace("{{question}}", question).replace("{{context}}", context)
        answer = await self.ollama.generate(self.app_settings.get_ollama_extraction_model(), prompt)
        response = AskResponse(
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
        ask_run = self._store_run(question, response)
        response.ask_run_id = ask_run.id
        return response

    def _store_run(self, question: str, response: AskResponse) -> AskRun:
        ask_run = AskRun(
            question=question,
            answer=response.answer,
            sources_json=[source.model_dump(mode="json") for source in response.sources],
        )
        self.db.add(ask_run)
        self.db.commit()
        self.db.refresh(ask_run)
        return ask_run

    def _prompt(self, filename: str) -> str:
        return (self.settings.prompt_dir / filename).read_text(encoding="utf-8")
