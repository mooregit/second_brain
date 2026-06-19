import base64
from pathlib import Path

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

    def generate_with_images_sync(self, model: str, prompt: str, image_paths: list[str]) -> str:
        images = [base64.b64encode(Path(path).read_bytes()).decode("ascii") for path in image_paths]
        with httpx.Client(base_url=self.settings.ollama_base_url, timeout=120) as client:
            response = client.post("/api/generate", json={"model": model, "prompt": prompt, "images": images, "stream": False})
            response.raise_for_status()
            return response.json()["response"]

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(base_url=self.settings.ollama_base_url, timeout=10) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
        return [self._model_info(model) for model in models]

    def _model_info(self, model: dict) -> dict:
        capabilities = model.get("capabilities") or []
        details = model.get("details") or {}
        name = model.get("name") or model.get("model") or ""
        supports_embedding = "embedding" in capabilities
        supports_completion = "completion" in capabilities or not capabilities
        return {
            "name": name,
            "model": model.get("model") or name,
            "size": model.get("size"),
            "modified_at": model.get("modified_at"),
            "details": details,
            "capabilities": capabilities,
            "supports_completion": supports_completion,
            "supports_embedding": supports_embedding,
            "parameter_size": details.get("parameter_size"),
            "context_length": details.get("context_length"),
            "embedding_length": details.get("embedding_length"),
        }
