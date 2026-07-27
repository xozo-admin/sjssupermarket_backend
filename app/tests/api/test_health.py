from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_production_frontend_cors_preflight() -> None:
    response = TestClient(app).options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://sjssupermarket.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://sjssupermarket.vercel.app"
    )
