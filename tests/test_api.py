import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1.routes import get_vision_provider
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


def test_openapi_docs_exposed(client):
    assert client.get("/openapi.json").status_code == 200


def test_frontend_served_at_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Menu Alchemist" in response.text
