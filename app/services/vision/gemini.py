from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.models.pantry import PantryScan
from app.models.recipe import Recipe
from app.services.vision.base import RateLimitError, VisionProvider, VisionProviderError
from app.services.vision.prompts import (
    build_invention_prompt,
    build_pantry_scan_prompt,
    build_prompt,
)


class GeminiProvider(VisionProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = genai.Client(api_key=api_key)

    async def _generate[T: BaseModel](
        self, contents: list, schema: type[T], temperature: float
    ) -> T:
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=temperature,
                ),
            )
        except errors.APIError as exc:
            if exc.code == 429:
                raise RateLimitError("Gemini free-tier rate limit hit") from exc
            raise VisionProviderError(f"Gemini API error ({exc.code}): {exc.message}") from exc

        if not response.text:
            raise VisionProviderError("Gemini returned an empty response")
        try:
            return schema.model_validate_json(response.text)
        except ValidationError as exc:
            raise VisionProviderError(f"Gemini returned invalid {schema.__name__} JSON: {exc}") from exc

    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe:
        return await self._generate(
            [
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                build_prompt(drink_name, description),
            ],
            Recipe,
            temperature=0.4,
        )

    async def identify_bottles(self, image_bytes: bytes, mime_type: str, hint: str) -> PantryScan:
        return await self._generate(
            [
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                build_pantry_scan_prompt(hint),
            ],
            PantryScan,
            # Reading labels is transcription, not creativity.
            temperature=0.1,
        )

    async def invent_recipe(self, inventory: list[str]) -> Recipe:
        return await self._generate(
            [build_invention_prompt(inventory)],
            Recipe,
            temperature=0.9,
        )
