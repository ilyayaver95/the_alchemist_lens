from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.models.recipe import Recipe
from app.services.vision.base import RateLimitError, VisionProvider, VisionProviderError
from app.services.vision.prompts import build_prompt


class GeminiProvider(VisionProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = genai.Client(api_key=api_key)

    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe:
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    build_prompt(drink_name, description),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Recipe,
                    temperature=0.4,
                ),
            )
        except errors.APIError as exc:
            if exc.code == 429:
                raise RateLimitError("Gemini free-tier rate limit hit") from exc
            raise VisionProviderError(f"Gemini API error ({exc.code}): {exc.message}") from exc

        if not response.text:
            raise VisionProviderError("Gemini returned an empty response")
        try:
            return Recipe.model_validate_json(response.text)
        except ValidationError as exc:
            raise VisionProviderError(f"Gemini returned invalid recipe JSON: {exc}") from exc
