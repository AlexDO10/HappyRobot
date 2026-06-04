"""End-to-end checks via the FastAPI TestClient, including the leak invariant."""

import os

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("FMCSA_MODE", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"x-api-key": "test-key"}


def test_health_is_unauthenticated():
    assert client.get("/health").status_code == 200


def test_endpoints_require_api_key():
    assert client.post("/get_loads", json={}).status_code == 401
    assert client.post("/get_loads", json={}, headers={"x-api-key": "wrong"}).status_code == 401


def test_get_loads_filters_and_strips_max_buy_rate():
    resp = client.post("/get_loads", json={"equipment_type": "Dry Van"}, headers=AUTH)
    assert resp.status_code == 200
    loads = resp.json()["loads"]
    assert loads, "expected at least one Dry Van load"
    for load in loads:
        assert load["equipment_type"] == "Dry Van"
        assert "max_buy_rate" not in load  # CRITICAL: ceiling must never leak


def test_max_buy_rate_never_appears_anywhere_in_get_loads_body():
    resp = client.post("/get_loads", json={}, headers=AUTH)
    assert "max_buy_rate" not in resp.text


def test_get_loads_substring_match_on_origin():
    resp = client.post("/get_loads", json={"origin": "dallas"}, headers=AUTH)
    assert [ld["load_id"] for ld in resp.json()["loads"]] == ["LD-1001"]


def test_verify_mc_mock():
    resp = client.post("/verify_mc", json={"mc_number": "123456"}, headers=AUTH)
    assert resp.json() == {"status": "eligible", "legal_name": "Mock Freight Lines LLC"}


def test_verify_mc_unknown_returns_not_found():
    # Only MC numbers explicitly in the mock registry resolve; everything else
    # (e.g. 000010) must be not_found, never eligible.
    resp = client.post("/verify_mc", json={"mc_number": "000010"}, headers=AUTH)
    assert resp.json()["status"] == "not_found"


def test_evaluate_offer_unknown_load_404():
    resp = client.post(
        "/evaluate_offer",
        json={"load_id": "NOPE", "carrier_offer": 100, "round": 1},
        headers=AUTH,
    )
    assert resp.status_code == 404


def test_evaluate_offer_response_omits_unused_fields():
    # accept -> only decision + agreed_rate; no counter_offer key.
    resp = client.post(
        "/evaluate_offer",
        json={"load_id": "LD-1001", "carrier_offer": 1850, "round": 1},
        headers=AUTH,
    )
    body = resp.json()
    assert body["decision"] == "accept"
    assert "counter_offer" not in body
