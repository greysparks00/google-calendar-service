from fastapi.testclient import TestClient
from Junction.services.relay.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_hello():
    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json()["message"] == "Hello from Junction!"


def test_echo():
    response = client.post(
        "/echo",
        json={"message": "Testing Junction"},
    )

    assert response.status_code == 200
    assert response.json()["echo"] == "Testing Junction"


def test_echo_validation():
    response = client.post(
        "/echo",
        json={},
    )

    assert response.status_code == 422
