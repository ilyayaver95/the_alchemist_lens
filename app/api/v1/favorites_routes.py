import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import Favorite, User
from app.models.favorites import FavoriteCreate, FavoriteSummary
from app.models.responses import AnalyzeResponse
from app.services.auth import get_current_user
from app.services.ingredients import normalize_name

router = APIRouter(prefix="/favorites")


def dedupe_key(body: FavoriteCreate) -> str:
    """Stable identity for a drink, so re-saving it never creates a second row."""
    if body.slug:
        return body.slug
    recipe = body.payload.recipe
    parts = [recipe.drink_name.strip().lower()]
    parts += sorted(normalize_name(i.name) for i in recipe.ingredients)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _summary(favorite: Favorite) -> FavoriteSummary:
    return FavoriteSummary(
        id=favorite.id,
        source=favorite.source,
        slug=favorite.slug,
        drink_name=favorite.drink_name,
        created_at=favorite.created_at,
    )


@router.get("", response_model=list[FavoriteSummary])
def list_favorites(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FavoriteSummary]:
    rows = db.execute(
        select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc(), Favorite.id.desc())
    ).scalars()
    return [_summary(row) for row in rows]


@router.post("", response_model=FavoriteSummary)
def save_favorite(
    body: FavoriteCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FavoriteSummary:
    key = dedupe_key(body)
    existing = db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.dedupe_key == key)
    ).scalar_one_or_none()
    if existing is not None:
        return _summary(existing)

    favorite = Favorite(
        user_id=user.id,
        source=body.source,
        slug=body.slug,
        drink_name=body.payload.recipe.drink_name,
        dedupe_key=key,
        payload=body.payload.model_dump_json(),
    )
    db.add(favorite)
    db.commit()
    return _summary(favorite)


def _owned(favorite_id: int, user: User, db: Session) -> Favorite:
    favorite = db.execute(
        select(Favorite).where(Favorite.id == favorite_id, Favorite.user_id == user.id)
    ).scalar_one_or_none()
    # 404 rather than 403 for someone else's id — no reason to confirm it exists.
    if favorite is None:
        raise HTTPException(404, detail="That favorite is no longer here.")
    return favorite


@router.get("/{favorite_id}", response_model=AnalyzeResponse)
def get_favorite(
    favorite_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalyzeResponse:
    return AnalyzeResponse.model_validate_json(_owned(favorite_id, user, db).payload)


@router.delete("/{favorite_id}", status_code=204)
def delete_favorite(
    favorite_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    db.delete(_owned(favorite_id, user, db))
    db.commit()
