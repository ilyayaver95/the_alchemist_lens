from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.auth import Credentials, UserPublic
from app.models.db_models import User
from app.services.auth import (
    COOKIE_NAME,
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth")


def _set_session_cookie(response: Response, user: User, settings: Settings) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_token(user.id, settings),
        max_age=settings.jwt_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/signup", response_model=UserPublic, status_code=201)
def signup(
    credentials: Credentials,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserPublic:
    email = credentials.email.strip().lower()
    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="That email is already registered — try signing in.")
    _set_session_cookie(response, user, settings)
    return UserPublic(id=user.id, email=user.email)


@router.post("/login", response_model=UserPublic)
def login(
    credentials: Credentials,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserPublic:
    email = credentials.email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    # Same message either way, so the endpoint can't be used to enumerate emails.
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, detail="Wrong email or password.")
    _set_session_cookie(response, user, settings)
    return UserPublic(id=user.id, email=user.email)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserPublic)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic(id=user.id, email=user.email)
