import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import create_app
from app.models import db_models  # noqa: F401  (registers the mappings)

CREDENTIALS = {"email": "ilya@example.com", "password": "correct horse battery"}


@pytest.fixture
def app_and_session():
    """A fresh in-memory database per test, shared across connections."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app_and_session):
    with TestClient(app_and_session) as test_client:
        yield test_client


@pytest.fixture
def signed_in(client):
    assert client.post("/api/v1/auth/signup", json=CREDENTIALS).status_code == 201
    return client


def sample_payload(client) -> dict:
    """A real AnalyzeResponse, straight from the classics library."""
    return client.get("/api/v1/classics/negroni").json()


class TestSignupAndLogin:
    def test_signup_sets_a_session_cookie(self, client):
        response = client.post("/api/v1/auth/signup", json=CREDENTIALS)
        assert response.status_code == 201
        assert response.json()["email"] == CREDENTIALS["email"]
        assert "alchemist_session" in client.cookies

    def test_duplicate_email_is_rejected(self, signed_in):
        response = signed_in.post("/api/v1/auth/signup", json=CREDENTIALS)
        assert response.status_code == 409

    def test_email_is_normalized(self, client):
        client.post("/api/v1/auth/signup", json={**CREDENTIALS, "email": "Ilya@Example.com "})
        assert client.post("/api/v1/auth/login", json=CREDENTIALS).status_code == 200

    def test_short_password_is_a_validation_error(self, client):
        response = client.post("/api/v1/auth/signup", json={**CREDENTIALS, "password": "short"})
        assert response.status_code == 422

    def test_wrong_password_is_rejected(self, signed_in):
        signed_in.post("/api/v1/auth/logout")
        response = signed_in.post(
            "/api/v1/auth/login", json={**CREDENTIALS, "password": "wrong but long enough"}
        )
        assert response.status_code == 401

    def test_unknown_email_gives_the_same_answer_as_a_wrong_password(self, client):
        response = client.post("/api/v1/auth/login", json=CREDENTIALS)
        assert response.status_code == 401
        assert response.json()["detail"] == "Wrong email or password."

    def test_me_requires_a_session(self, client):
        assert client.get("/api/v1/auth/me").status_code == 401

    def test_logout_clears_the_session(self, signed_in):
        assert signed_in.get("/api/v1/auth/me").status_code == 200
        assert signed_in.post("/api/v1/auth/logout").status_code == 204
        assert signed_in.get("/api/v1/auth/me").status_code == 401

    def test_a_tampered_cookie_is_not_a_session(self, client):
        client.cookies.set("alchemist_session", "not.a.jwt")
        assert client.get("/api/v1/auth/me").status_code == 401


class TestFavorites:
    def test_signed_out_users_cannot_save(self, client):
        response = client.post(
            "/api/v1/favorites", json={"source": "classic", "slug": "negroni", "payload": sample_payload(client)}
        )
        assert response.status_code == 401

    def test_save_then_list_then_fetch(self, signed_in):
        payload = sample_payload(signed_in)
        saved = signed_in.post(
            "/api/v1/favorites", json={"source": "classic", "slug": "negroni", "payload": payload}
        )
        assert saved.status_code == 200
        assert saved.json()["drink_name"] == "Negroni"

        listed = signed_in.get("/api/v1/favorites").json()
        assert [f["slug"] for f in listed] == ["negroni"]

        full = signed_in.get(f"/api/v1/favorites/{saved.json()['id']}").json()
        assert full["recipe"]["drink_name"] == "Negroni"
        assert full["buy_list"]["groups"]

    def test_saving_twice_is_a_no_op(self, signed_in):
        body = {"source": "classic", "slug": "negroni", "payload": sample_payload(signed_in)}
        first = signed_in.post("/api/v1/favorites", json=body).json()
        second = signed_in.post("/api/v1/favorites", json=body).json()
        assert first["id"] == second["id"]
        assert len(signed_in.get("/api/v1/favorites").json()) == 1

    def test_analyzed_drinks_dedupe_without_a_slug(self, signed_in):
        body = {"source": "analyze", "payload": sample_payload(signed_in)}
        signed_in.post("/api/v1/favorites", json=body)
        signed_in.post("/api/v1/favorites", json=body)
        assert len(signed_in.get("/api/v1/favorites").json()) == 1

    def test_delete(self, signed_in):
        saved = signed_in.post(
            "/api/v1/favorites",
            json={"source": "classic", "slug": "negroni", "payload": sample_payload(signed_in)},
        ).json()
        assert signed_in.delete(f"/api/v1/favorites/{saved['id']}").status_code == 204
        assert signed_in.get("/api/v1/favorites").json() == []

    def test_favorites_are_scoped_to_their_owner(self, signed_in):
        saved = signed_in.post(
            "/api/v1/favorites",
            json={"source": "classic", "slug": "negroni", "payload": sample_payload(signed_in)},
        ).json()
        signed_in.post("/api/v1/auth/logout")
        signed_in.post(
            "/api/v1/auth/signup", json={"email": "other@example.com", "password": "another long one"}
        )
        assert signed_in.get("/api/v1/favorites").json() == []
        # Someone else's id reads as gone, not as forbidden.
        assert signed_in.get(f"/api/v1/favorites/{saved['id']}").status_code == 404
        assert signed_in.delete(f"/api/v1/favorites/{saved['id']}").status_code == 404
