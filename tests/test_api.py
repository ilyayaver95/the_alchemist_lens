import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1.routes import get_optional_vision_provider, get_vision_provider
from app.config import Settings, get_settings
from app.main import create_app
from app.services.vision.fake import FakeProvider


def make_image_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (30, 90, 60)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    app = create_app()
    test_settings = Settings(
        vision_provider="fake",
        cache_enabled=True,
        cache_dir=str(tmp_path / "cache"),
        _env_file=None,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_vision_provider] = FakeProvider
    app.dependency_overrides[get_optional_vision_provider] = FakeProvider
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "fake"


def test_analyze_end_to_end(client):
    response = client.post(
        "/api/v1/analyze",
        files={"image": ("drink.jpg", make_image_bytes(), "image/jpeg")},
        data={"name": "Midnight in Oaxaca", "description": "mezcal, citrus, chili salt"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recipe"]["drink_name"] == "Midnight in Oaxaca"
    assert body["recipe"]["ingredients"]
    assert body["recipe"]["steps"]
    assert body["provider"] == "fake"
    assert body["cached"] is False
    # buy list excludes staples (ice) and groups the rest
    group_labels = [g["label"] for g in body["buy_list"]["groups"]]
    assert "Spirits" in group_labels
    assert body["buy_list"]["staples_assumed"] == ["crushed ice"]


def test_analyze_cached_on_second_call(client):
    image = make_image_bytes()
    request = {
        "files": {"image": ("drink.jpg", image, "image/jpeg")},
        "data": {"name": "Paloma", "description": "tequila and grapefruit"},
    }
    assert client.post("/api/v1/analyze", **request).json()["cached"] is False
    assert client.post("/api/v1/analyze", **request).json()["cached"] is True


def test_rejects_non_image_content_type(client):
    response = client.post(
        "/api/v1/analyze",
        files={"image": ("notes.txt", b"hello", "text/plain")},
        data={"name": "Test"},
    )
    assert response.status_code == 415


def test_rejects_undecodable_image(client):
    response = client.post(
        "/api/v1/analyze",
        files={"image": ("fake.jpg", b"not really a jpeg", "image/jpeg")},
        data={"name": "Test"},
    )
    assert response.status_code == 422


def test_missing_name_is_validation_error(client):
    response = client.post(
        "/api/v1/analyze",
        files={"image": ("drink.jpg", make_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 422


def test_analyze_includes_paneco_links(client):
    body = client.post(
        "/api/v1/analyze",
        files={"image": ("drink.jpg", make_image_bytes(), "image/jpeg")},
        data={"name": "Smoky Margarita"},
    ).json()
    spirits = next(g for g in body["buy_list"]["groups"] if g["label"] == "Spirits")
    assert spirits["items"][0]["paneco_url"].startswith("https://www.paneco.co.il/catalogsearch/")
    assert body["buy_list"]["paneco_sale_url"].endswith("/special-offers")


class TestClassics:
    def test_list(self, client):
        body = client.get("/api/v1/classics").json()
        assert len(body) >= 20
        assert {"slug", "drink_name", "summary", "tags"} <= body[0].keys()

    def test_detail_is_shaped_like_an_analysis(self, client):
        body = client.get("/api/v1/classics/negroni").json()
        assert body["recipe"]["drink_name"] == "Negroni"
        assert body["provider"] == "library"
        assert body["buy_list"]["groups"]

    def test_unknown_slug(self, client):
        assert client.get("/api/v1/classics/nonexistent").status_code == 404


class TestPantry:
    def test_scan_reads_the_shelf(self, client):
        body = client.post(
            "/api/v1/pantry/scan",
            files={"image": ("shelf.jpg", make_image_bytes(), "image/jpeg")},
            data={"hint": "kitchen counter"},
        ).json()
        assert [item["name"] for item in body["items"]]

    def test_scan_rejects_non_images(self, client):
        response = client.post(
            "/api/v1/pantry/scan", files={"image": ("notes.txt", b"hello", "text/plain")}
        )
        assert response.status_code == 415

    def test_suggest_matches_classics_without_an_llm(self, client):
        body = client.post(
            "/api/v1/pantry/suggest",
            json={"items": ["gin", "Campari", "sweet vermouth"], "invent": False},
        ).json()
        assert "Negroni" in [m["drink_name"] for m in body["makeable"]]
        assert body["invention"] is None

    def test_suggest_can_also_invent(self, client):
        body = client.post(
            "/api/v1/pantry/suggest", json={"items": ["gin", "tonic water"], "invent": True}
        ).json()
        assert body["invention"]["recipe"]["drink_name"]
        assert body["invention"]["buy_list"]["groups"]

    def test_suggest_needs_at_least_one_item(self, client):
        assert client.post("/api/v1/pantry/suggest", json={"items": []}).status_code == 422


def test_openapi_docs_exposed(client):
    assert client.get("/openapi.json").status_code == 200


def test_frontend_served_at_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Menu Alchemist" in response.text
