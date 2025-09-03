import sys
import pathlib

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

# Ensure project root on sys.path for test collection when running directly
ROOT = pathlib.Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import soegemaskine.searchapi.dhosearch as dhosearch  # type: ignore

ADMIN_TOKEN = "secret-token"

def _enable_admin(monkeypatch, allow_view: bool = True):
    monkeypatch.setenv("ADMIN_ENABLED", "true")
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("ADMIN_ALLOW_CONFIG_VIEW", "true" if allow_view else "false")
    # Update both central config singleton and the module-level cached _cfg
    dhosearch._cfg = dhosearch.refresh_config()

@pytest.mark.anyio
async def test_configz_not_enabled_returns_404(monkeypatch):
    # Ensure disabled state (default) then refresh
    monkeypatch.delenv("ADMIN_ENABLED", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    dhosearch._cfg = dhosearch.refresh_config()
    async with AsyncClient(transport=ASGITransport(app=dhosearch.app), base_url="http://test") as ac:
        r = await ac.get("/configz")
        assert r.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.anyio
async def test_configz_unauthorized_when_enabled(monkeypatch):
    _enable_admin(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=dhosearch.app), base_url="http://test") as ac:
        r = await ac.get("/configz")
        assert r.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.anyio
async def test_configz_authorized_masks_secrets(monkeypatch):
    _enable_admin(monkeypatch)
    monkeypatch.setenv("POSTGRES_PASSWORD", "supersecret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-123")
    dhosearch._cfg = dhosearch.refresh_config()
    async with AsyncClient(transport=ASGITransport(app=dhosearch.app), base_url="http://test") as ac:
        r = await ac.get("/configz", headers={"x-admin-token": ADMIN_TOKEN})
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert data["database"]["password"] == "***"
        assert data["provider"]["openai_api_key"] == "***"
        assert data["service_version"] == dhosearch._cfg.service.version

@pytest.mark.anyio
async def test_refresh_config_changes_distance_threshold(monkeypatch):
    _enable_admin(monkeypatch)
    # initial baseline apply and refresh
    monkeypatch.setenv("DISTANCE_THRESHOLD", "0.33")
    dhosearch._cfg = dhosearch.refresh_config()
    async with AsyncClient(transport=ASGITransport(app=dhosearch.app), base_url="http://test") as ac:
        r1 = await ac.post("/admin/refresh-config", headers={"x-admin-token": ADMIN_TOKEN})
        assert r1.status_code == status.HTTP_200_OK
    # change env then refresh again
    monkeypatch.setenv("DISTANCE_THRESHOLD", "0.44")
    async with AsyncClient(transport=ASGITransport(app=dhosearch.app), base_url="http://test") as ac:
        r2 = await ac.post("/admin/refresh-config", headers={"x-admin-token": ADMIN_TOKEN})
        assert r2.status_code == status.HTTP_200_OK
    # Now central config should reflect new value
    assert abs(dhosearch._cfg.search.distance_threshold - 0.44) < 1e-9

@pytest.mark.anyio
async def test_refresh_config_unauthorized(monkeypatch):
    _enable_admin(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=dhosearch.app), base_url="http://test") as ac:
        r = await ac.post("/admin/refresh-config")
        assert r.status_code == status.HTTP_401_UNAUTHORIZED
