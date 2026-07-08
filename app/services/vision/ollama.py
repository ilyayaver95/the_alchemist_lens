import base64

import httpx
from pydantic import ValidationError

from app.models.recipe import Recipe
from app.services.vision.base import VisionProvider, VisionProviderError
from app.services.vision.prompts import build_prompt


class OllamaProvider(VisionProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.model = model
        self._base_url = base_url.rstrip("/")

    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe:
        payload = {
            "model": self.model,
            "stream": False,
            "format": Recipe.model_json_schema(),
            "options": {"temperature": 0.4},
            "messages": [
                {
                    "role": "user",
                    "content": build_prompt(drink_name, description),
                    "images": [base64.b64encode(image_bytes).decode("ascii")],
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise VisionProviderError(
                f"Cannot reach Ollama at {self._base_url} — is `ollama serve` running?"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise VisionProviderError(f"Ollama error: {exc.response.text[:500]}") from exc

        content = response.json().get("message", {}).get("content", "")
        try:
            return Recipe.model_validate_json(content)
        except ValidationError as exc:
            raise VisionProviderError(f"Ollama returned invalid recipe JSON: {exc}") from exc
