import base64

import httpx
from pydantic import BaseModel, ValidationError

from app.models.pantry import PantryScan
from app.models.recipe import Recipe
from app.services.vision.base import VisionProvider, VisionProviderError
from app.services.vision.prompts import (
    build_invention_prompt,
    build_pantry_scan_prompt,
    build_prompt,
)


class OllamaProvider(VisionProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.model = model
        self._base_url = base_url.rstrip("/")

    async def _chat[T: BaseModel](
        self, prompt: str, schema: type[T], image_bytes: bytes | None, temperature: float
    ) -> T:
        message: dict = {"role": "user", "content": prompt}
        if image_bytes is not None:
            message["images"] = [base64.b64encode(image_bytes).decode("ascii")]
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {"temperature": temperature},
            "messages": [message],
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
            return schema.model_validate_json(content)
        except ValidationError as exc:
            raise VisionProviderError(f"Ollama returned invalid {schema.__name__} JSON: {exc}") from exc

    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe:
        return await self._chat(build_prompt(drink_name, description), Recipe, image_bytes, 0.4)

    async def identify_bottles(self, image_bytes: bytes, mime_type: str, hint: str) -> PantryScan:
        return await self._chat(build_pantry_scan_prompt(hint), PantryScan, image_bytes, 0.1)

    async def invent_recipe(self, inventory: list[str]) -> Recipe:
        return await self._chat(build_invention_prompt(inventory), Recipe, None, 0.9)
