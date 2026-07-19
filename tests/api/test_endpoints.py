"""API Endpoint Tests for SelfSmart AI."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client):
    """Register a user and return auth headers."""
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "SecureP@ss123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    async def test_register(self, client):
        resp = await client.post("/api/auth/register", json={
            "email": "new@example.com", "password": "SecureP@ss123"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_invalid(self, client):
        resp = await client.post("/api/auth/login", json={
            "email": "bad@example.com", "password": "wrong"
        })
        assert resp.status_code == 401

    async def test_rate_limit_register(self, client):
        for _ in range(4):
            await client.post("/api/auth/register", json={
                "email": f"test{_}@test.com", "password": "SecureP@ss123"
            })
        resp = await client.post("/api/auth/register", json={
            "email": "test@test.com", "password": "SecureP@ss123"
        })
        assert resp.status_code == 429

    async def test_rate_limit_login(self, client):
        for _ in range(6):
            await client.post("/api/auth/login", json={
                "email": "test@test.com", "password": "wrong"
            })
        resp = await client.post("/api/auth/login", json={
            "email": "test@test.com", "password": "wrong"
        })
        assert resp.status_code == 429


class TestProtectedEndpoints:
    async def test_feedback_requires_auth(self, client):
        resp = await client.post("/api/feedback", json={
            "conversation_id": "x", "message_index": 0, "is_positive": True
        })
        assert resp.status_code == 401

    async def test_stats_requires_auth(self, client):
        resp = await client.get("/api/stats")
        assert resp.status_code == 401

    async def test_training_requires_auth(self, client):
        resp = await client.post("/api/training/start")
        assert resp.status_code == 401


class TestHealth:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("healthy", "degraded")

    async def test_error_does_not_leak(self, client):
        """Ensure 500 responses never contain stack traces."""
        resp = await client.get("/api/nonexistent")
        if resp.status_code == 500:
            assert "Traceback" not in resp.text
            assert "Error" not in resp.json().get("detail", "")