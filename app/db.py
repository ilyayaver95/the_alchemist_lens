"""SQLAlchemy engine and session wiring.

One `DATABASE_URL` drives both environments: a SQLite file for local development
(zero setup) and Postgres on Render (survives redeploys).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _normalize(url: str) -> str:
    """Render hands out `postgres://` URLs, which SQLAlchemy 2 no longer accepts."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _make_engine():
    url = _normalize(get_settings().database_url)
    # SQLite refuses cross-thread connections by default, and FastAPI's
    # threadpool hands sync endpoints to whichever worker thread is free.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    # Two tables and no history to migrate — create_all is honest here. Swap in
    # Alembic the first time a column has to change on live data.
    from app.models import db_models  # noqa: F401  (registers the mappings)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
