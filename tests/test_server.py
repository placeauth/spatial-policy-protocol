from __future__ import annotations

import asyncio

import httpx

from spp.server import app


def call(method: str, path: str, **kwargs) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(request())


def test_health() -> None:
    response = call("GET", "/health")
    assert response.status_code == 200
    assert response.json()["spp_version"] == "0.1"


def test_decision_endpoint() -> None:
    response = call(
        "POST",
        "/v1/decision",
        json={
            "spp_version": "0.1",
            "request_id": "api-1",
            "actor": {"id": "robot:test:1", "type": "delivery_robot"},
            "space": "clinic/pharmacy",
            "action": {"family": "movement", "name": "enter"},
            "context": {"purpose": "package_delivery"},
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "deny"


def test_invalid_request_is_422() -> None:
    response = call("POST", "/v1/decision", json={"space": "clinic/lobby"})
    assert response.status_code == 422
