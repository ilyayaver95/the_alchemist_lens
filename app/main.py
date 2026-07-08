import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes import router as v1_router

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Menu Alchemist",
        version="0.1.0",
        description=(
            "Turn a photo of a menu drink plus its name/description into a structured "
            "recipe and a categorized shopping list. Designed to be consumed by any "
            "client (web, iOS) via the versioned REST API."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
    return app


app = create_app()
