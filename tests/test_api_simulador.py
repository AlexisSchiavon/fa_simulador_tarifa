"""Tests básicos de la API — Fase 1 (solo healthcheck y rutas del seed)."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "Hyperred" in data["app"]


def test_rutas_endpoint_exists(client):
    resp = client.get("/api/rutas/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_viajes_endpoint_exists(client):
    resp = client.get("/api/viajes/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
