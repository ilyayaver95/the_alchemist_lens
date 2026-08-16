import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.favorites_routes import router as favorites_router
from app.api.v1.routes import router as v1_router
from app.db import init_db

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Menu Alchemist",
        version="0.2.0",
        description=(
            "Turn a photo of a menu drink plus its name/description into a structured "
            "recipe and a categorized shopping list. Also serves a library of classic "
            "cocktails, home-bar matching, accounts, and favorites. Designed to be "
            "consumed by any client (web, iOS) via the versioned REST API."
        ),
    )
    # Wide open so a future native client can hit the same API. Note that this is
    # incompatible with allow_credentials=True — the session cookie works because
    # the web UI is served same-origin. Narrow the origins before turning that on.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    init_db()
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
    app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
    app.include_router(favorites_router, prefix="/api/v1", tags=["favorites"])
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
    return app


app = create_app()
