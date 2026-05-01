"""Tests for approval gate API."""

from fastapi.testclient import TestClient
from cab.api.gate import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_non_production_always_allowed() -> None:
    response = client.post("/gate/check", json={
        "service_name": "payments-api",
        "environment": "staging",
    })
    assert response.status_code == 200
    assert response.json()["allowed"] is True


def test_production_without_ticket_blocked() -> None:
    response = client.post("/gate/check", json={
        "service_name": "payments-api",
        "environment": "production",
    })
    assert response.status_code == 200
    assert response.json()["allowed"] is False


def test_production_with_ticket_approved() -> None:
    response = client.post("/gate/check", json={
        "service_name": "payments-api",
        "environment": "production",
        "snow_ticket": "CHG0012345",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True


def test_list_pending_requests_empty() -> None:
    response = client.get("/gate/requests")
    assert response.status_code == 200
    assert "requests" in response.json()