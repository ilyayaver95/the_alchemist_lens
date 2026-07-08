# ⚗️ Menu Alchemist

Point it at any drink on a menu — get the likely recipe and a shopping list.

Upload a photo of a drink (or of the menu itself), add the drink's name and menu
description, and Menu Alchemist uses a vision-capable LLM to reconstruct a
plausible recipe: ingredients with amounts, preparation steps, glassware,
garnish, and estimated ABV. It then builds a **buy list** — only the things you
don't already have, grouped by category, with realistic bottle/package sizes and
per-bottle serving estimates.

## Architecture

- **FastAPI backend** with a versioned REST API (`/api/v1`), documented via
  OpenAPI at `/docs`. All business logic lives in the backend so a future native
  client (e.g. SwiftUI iOS app) can consume the same API.
- **Pluggable vision providers** behind a small `VisionProvider` interface
  (`app/services/vision/`): Google **Gemini** (free tier, default), **Ollama**
  (fully local/offline), and a **fake** provider for tests and demos. Swap with
  one env var.
- **Deterministic buy-list logic** (`app/services/buy_list.py`): the LLM only
  extracts the recipe; pantry-staple detection, category grouping, package
  sizing, and serving estimates are pure Python — fully unit-tested, no API
  calls.
- **Response cache** keyed on image + text, so repeated requests don't burn
  free-tier quota.
- **Vanilla HTML/CSS/JS frontend** served by the same app at `/` — no build step.

```
app/
├── main.py                  # FastAPI app: API + static frontend
├── config.py                # settings from environment / .env
├── api/v1/routes.py         # POST /analyze, GET /health
├── models/                  # Recipe, Ingredient, BuyList (Pydantic)
├── services/
│   ├── vision/              # provider interface + gemini / ollama / fake
│   ├── recipe_service.py    # image prep, caching, retry, orchestration
│   └── buy_list.py          # staples + package-size logic (pure Python)
└── static/                  # the web UI
tests/
```

## Setup

Requires Python 3.12+.

```bash
python3 -m venv .venv            # skip if .venv already exists
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
```

### Option A: Gemini (recommended, free)

1. Get a free API key at [aistudio.google.com](https://aistudio.google.com)
   (no credit card required).
2. In `.env`, set:

   ```
   VISION_PROVIDER=gemini
   GEMINI_API_KEY=your-key-here
   ```

### Option B: Ollama (fully offline)

1. Install [Ollama](https://ollama.com) and pull a vision model:

   ```bash
   ollama pull qwen2.5vl:7b
   ```

2. In `.env`, set `VISION_PROVIDER=ollama` (and make sure `ollama serve` is
   running). Expect slower responses and somewhat lower extraction quality
   than Gemini.

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
```

- Web app: <http://127.0.0.1:8000>
- API docs (Swagger): <http://127.0.0.1:8000/docs>

To try the UI without any AI configured, run with the canned provider:

```bash
VISION_PROVIDER=fake .venv/bin/uvicorn app.main:app --reload
```

## API

| Endpoint | Description |
| --- | --- |
| `POST /api/v1/analyze` | Multipart form: `image` (JPEG/PNG/WebP, ≤10 MB), `name`, `description` (optional). Returns the structured recipe + grouped buy list. |
| `GET /api/v1/health` | Reports status and the active provider/model. |

Errors are meaningful: `415` bad file type, `413` too large, `422` undecodable
image, `429` free-tier quota exhausted (after automatic retries), `502` provider
failure, `503` provider not configured.

## Tests

```bash
.venv/bin/python -m pytest
```

Covers buy-list logic (staples, grouping, package sizes, serving math, dedupe),
image preparation, caching, rate-limit retry behavior, and the API end-to-end
via the fake provider — no network or API key needed.

## Configuration

All settings come from environment variables / `.env` (see `.env.example`):
provider selection, Gemini/Ollama model names, cache location, upload limits.
Secrets are never committed — `.env` is gitignored.
