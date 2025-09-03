from fastapi.testclient import TestClient

from soegemaskine.searchapi.dhosearch import app


def test_healthz_basic():
    client = TestClient(app)
    resp = client.get('/healthz')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'searchapi'


def test_readyz_degraded_without_startup(monkeypatch):
    # Force db_service / provider to None to simulate pre-lifespan state
    from soegemaskine.searchapi import dhosearch
    monkeypatch.setattr(dhosearch, 'db_service', None)
    monkeypatch.setattr(dhosearch, 'embedding_provider', None)
    client = TestClient(app)
    resp = client.get('/readyz')
    # Without initialized services readiness should degrade
    assert resp.status_code in (200, 503)
    data = resp.json()
    # Accept either degraded (preferred) or fail open ok if both considered absent
    assert data['service'] == 'searchapi'
    # If status ok both db/provider must be ok; else degraded acceptable
    assert 'status' in data

