# ⚗️ Menu Alchemist

Point it at any drink on a menu — get the likely recipe and a shopping list.

Upload a photo of a drink (or of the menu itself), add the drink's name and menu
description, and Menu Alchemist uses a vision-capable LLM to reconstruct a
plausible recipe: ingredients with amounts, preparation steps, glassware,
garnish, and estimated ABV. It then builds a **buy list** — only the things you
don't already have, grouped by category, with realistic bottle/package sizes and
per-bottle serving estimates.

Four screens, all built on that same recipe shape:

| Screen | What it does |
| --- | --- |
| **📷 Analyze** | Photo of a menu drink → recipe + buy list. |
| **📖 Classics** | Twenty hand-written classics, each with its own buy list. No AI call. |
| **🫙 My Bar** | Type your bottles or photograph the shelf; get what you can make now and what you're one or two bottles short of, plus an optional AI original built only from what you own. |
| **♡ Favorites** | Keep any drink to your account, on every device you sign in from. |

Every buy list ends with **🛒 Build bucket list in Paneco** — one deep link per
bottle into [paneco.co.il](https://www.paneco.co.il), cheapest first so sale
prices surface, plus a link to their promotions page.

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
  sizing, serving estimates, and Paneco term selection are pure Python — fully
  unit-tested, no API calls.
- **A shared ingredient vocabulary** (`app/services/ingredients.py`): one place
  that knows "crushed ice" is ice, "Tanqueray gin" is gin, and Cointreau
  satisfies a recipe asking for triple sec. The buy list, the Paneco linker, and
  the home-bar matcher all read from it.
- **Home-bar matching is deterministic too** (`app/services/pantry.py`): no
  model call is needed to work out that gin, Campari, and sweet vermouth make a
  Negroni. The LLM is only used to read a shelf photo and, optionally, to invent
  an original.
- **Accounts and favorites** on SQLAlchemy over one `DATABASE_URL` — SQLite
  locally, Postgres in production. Email + password, bcrypt, JWT in an httpOnly
  cookie.
- **Response cache** keyed on image + text, so repeated requests don't burn
  free-tier quota.
- **Vanilla HTML/CSS/JS frontend** served by the same app at `/` — native ES
  modules and a twenty-line hash router, no build step and no dependencies.

```
app/
├── main.py                  # FastAPI app: API + static frontend
├── config.py                # settings from environment / .env
├── db.py                    # SQLAlchemy engine/session from DATABASE_URL
├── data/classics.json       # the bundled cocktail library
├── api/v1/
│   ├── routes.py            # analyze, classics, pantry, health
│   ├── auth_routes.py       # signup / login / logout / me
│   └── favorites_routes.py  # favorites CRUD
├── models/                  # Recipe, BuyList, Classic, Pantry, DB models
├── services/
│   ├── vision/              # provider interface + gemini / ollama / fake
│   ├── ingredients.py       # normalization, staples, ingredient families
│   ├── recipe_service.py    # image prep, caching, orchestration
│   ├── pantry.py            # home-bar matching (pure Python)
│   ├── classics.py          # loads + validates the library
│   ├── paneco.py            # retailer deep links (pure functions)
│   └── buy_list.py          # staples + package-size logic (pure Python)
└── static/                  # the web UI (ES modules, views/ per screen)
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
| `GET /api/v1/classics` | The library, as lightweight summaries for a browse grid. |
| `GET /api/v1/classics/{slug}` | One classic, shaped as an `AnalyzeResponse` so every client renders it with the same code. |
| `POST /api/v1/pantry/scan` | Multipart form: `image`, `hint` (optional). Reads bottles off a shelf photo. |
| `POST /api/v1/pantry/suggest` | JSON `{items, invent}`. Deterministic classic matching; `invent` adds one AI original. Works with no AI provider configured. |
| `POST /api/v1/auth/signup` · `login` · `logout` · `GET /auth/me` | Email + password; sets an httpOnly session cookie. |
| `GET/POST /api/v1/favorites`, `GET/DELETE /api/v1/favorites/{id}` | Saved drinks, scoped to the signed-in user. Saving the same drink twice is a no-op. |
| `GET /api/v1/health` | Reports status and the active provider/model. |

Errors are meaningful: `401` not signed in / bad credentials, `409` email taken,
`413` too large, `415` bad file type, `422` undecodable image, `429` free-tier
quota exhausted (after automatic retries), `501` provider lacks that capability,
`502` provider failure, `503` provider not configured.

### The Paneco links

Every `BuyListItem` for something a liquor store stocks carries `paneco_query`
and `paneco_url`; produce, garnishes, and dairy carry neither, so there are no
dead links. The URLs point at Paneco's Magento search
(`/catalogsearch/result/?q=…&product_list_order=price&product_list_dir=asc`),
and `BuyList.paneco_sale_url` points at `/special-offers`.

Link building itself reads nothing: `app/services/paneco.py` is pure functions
over a term table mixing the store's own Hebrew category words (ג'ין, וודקה,
רום) with English brand names, both of which their search indexes. That table
is the part most likely to need occasional attention.

### Sale badges

`app/services/paneco_sales.py` is the one component that *reads* Paneco, so
that a buy list can say which bottles are discounted. Its constraints are
deliberate:

- **Plain paths only.** Category pages (`/gin`, `/whiskey`, `/liqueur`, …) and
  `/special-offers`. Their `robots.txt` disallows `/catalogsearch/` and every
  query-string URL, so nothing here paginates, sorts or searches — which caps
  us at the first page of each category.
- **Browser headers**, because the origin returns 403 to non-browser clients.
  A deliberate choice, not an accident.
- **Fetched once, cached for `PANECO_SALES_TTL_HOURS`** (default 12) across all
  categories at once — never per ingredient, and never a partial index, since a
  partial one would be cached and then answer "no discount" for every later drink.
- **Fails soft.** No sale data means no badges; links, buy list and recipe are
  unaffected. `PANECO_SALES_ENABLED=false` turns it back into a pure link builder.

Two rules keep the badges honest:

1. **Only positive claims.** No badge means we found no discount in the slice we
   read — never that the bottle is full price.
2. **Attribution before assertion.** Sitting on a dedicated category page is
   proof enough for gin or rum, but a dozen families share `/liqueur`, so there
   a product must name itself (`קמפרי` → Campari). Otherwise Campari would
   inherit a discount on banana liqueur for sharing a shelf.

The badge shows the **deepest discount**, not the lowest price — the cheapest
discounted bottle is usually a 50 ml miniature, which those are filtered out
anyway. Within a category the match is family-level, so a tequila badge may name
an añejo when you asked for blanco; the product name is always shown so the
reader can judge.

## Use it on your iPhone (PWA)

The web app is installable. Once the backend is reachable from your phone
(see deployment below), open the URL in Safari, tap **Share → Add to Home
Screen**, and you get a full-screen app with its own icon. Tapping the photo
area opens the camera directly; photos are downscaled on-device before upload,
so it's fast on cellular and iPhone HEIC photos are handled automatically.

## Deploy to Render (free)

The repo contains a `render.yaml` blueprint.

1. Push this repo to GitHub.
2. Create a free account at [render.com](https://render.com), then
   **New → Blueprint**, pick the repo, and apply.
3. When prompted, set `GEMINI_API_KEY` to your key (it's marked `sync: false`,
   so it lives only in Render's dashboard, never in git). The blueprint also
   provisions a free Postgres instance for accounts and favorites, generates
   `JWT_SECRET`, and sets `COOKIE_SECURE=true`.
4. Open `https://<your-service>.onrender.com` on your iPhone and add it to
   your home screen.

The schema is created with `Base.metadata.create_all` at startup — fine for two
tables with no history, but the first time a column has to change on live data,
add Alembic rather than editing the model in place.

Free-tier caveat: the server sleeps after ~15 minutes of inactivity, so the
first request after a while takes up to a minute while it wakes — the app's
loading state covers this.

## Tests

```bash
.venv/bin/python -m pytest
```

106 tests, no network and no API key needed. They cover buy-list logic (staples,
grouping, package sizes, serving math, dedupe), ingredient families and
brand-prefixed shelf names, home-bar matching, Paneco URL construction, sale
parsing and attribution, image preparation, caching, rate-limit retry, auth and
per-user favorite isolation, and every endpoint end-to-end via the fake provider.

Sale parsing is tested against `tests/fixtures/paneco_sale_page.html`, real
markup captured from a listing page, so the parser is pinned to what the site
actually emits rather than to a hand-written imitation of it.

`tests/conftest.py` points `DATABASE_URL` at a temp file before the app is
imported and sets `PANECO_SALES_ENABLED=false`, so running the suite touches
neither your dev database nor the network.

## Configuration

All settings come from environment variables / `.env` (see `.env.example`):
provider selection, Gemini/Ollama model names, cache location, upload limits,
`DATABASE_URL`, `JWT_SECRET`, `COOKIE_SECURE`, `PANECO_BASE_URL`,
`PANECO_SALES_ENABLED`, `PANECO_SALES_TTL_HOURS`, and `ENABLE_INVENTION`.
Secrets are never committed — `.env` is gitignored. Startup fails fast if
`COOKIE_SECURE=true` while `JWT_SECRET` is still the dev default, since a
guessable signing key would let anyone forge a session.
