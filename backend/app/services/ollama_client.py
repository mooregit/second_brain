import httpx

from app.core.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(self, model: str, prompt: str) -> str:
        async with httpx.AsyncClient(base_url=self.settings.ollama_base_url, timeout=120) as client:
            response = await client.post("/api/generate", json={"model": model, "prompt": prompt, "stream": False})
            response.raise_for_status()
            return response.json()["response"]

    async def embed(self, model: str, text: str) -> list[float]:
        async with httpx.AsyncClient(base_url=self.settings.ollama_base_url, timeout=120) as client:
            response = await client.post("/api/embeddings", json={"model": model, "prompt": text})
            response.raise_for_status()
            return response.json()["embedding"]

