from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/api/v1/health')
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


def test_ping_and_root():
    assert client.get("/api/v1/ping").json() == {"ping": "pong"}
    assert client.get("/").json()["message"].startswith("Language Practice Service")


def test_root_health_and_metrics():
    request_id = "test-request-id"
    response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert "language_practice_http_requests_total" in metrics.text
