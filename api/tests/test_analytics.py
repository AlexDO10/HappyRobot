"""Tests for the call-results analytics endpoints (dashboard backend)."""

import os
import tempfile

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("FMCSA_MODE", "mock")
# Use a throwaway DB so tests don't touch the real analytics file.
os.environ["CALLS_DB"] = os.path.join(tempfile.mkdtemp(), "test_calls.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"x-api-key": "test-key"}


def test_log_and_list_call_result():
    payload = {
        "mc_number": "123456",
        "load_id": "LD-1001",
        "outcome": "booked",
        "sentiment": "positive",
        "final_rate": 2000,
        "negotiation_rounds": 2,
        "transcript_summary": "Booked after one counter.",
    }
    resp = client.post("/call_results", json=payload, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] >= 1
    assert body["outcome"] == "booked"
    assert "created_at" in body

    listed = client.get("/call_results", headers=AUTH).json()
    assert any(c["load_id"] == "LD-1001" for c in listed)


def test_metrics_aggregates():
    client.post(
        "/call_results",
        json={"outcome": "no_agreement", "sentiment": "negative", "negotiation_rounds": 3},
        headers=AUTH,
    )
    m = client.get("/metrics", headers=AUTH).json()
    assert m["total_calls"] >= 2
    assert "booked" in m["outcomes"]
    assert "positive" in m["sentiments"]
    assert 0.0 <= m["booking_rate"] <= 1.0


def test_call_result_tolerates_blank_fields():
    # Empty strings (how HappyRobot sends unfilled variables) must not 422.
    payload = {
        "mc_number": "",
        "load_id": "",
        "outcome": "",
        "sentiment": "",
        "final_rate": "",
        "negotiation_rounds": "",
        "transcript_summary": "",
    }
    resp = client.post("/call_results", json=payload, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "abandoned"
    assert body["sentiment"] == "neutral"
    assert body["final_rate"] is None
    assert body["negotiation_rounds"] == 0


def test_call_result_coerces_numeric_strings():
    payload = {"outcome": "booked", "final_rate": "2000", "negotiation_rounds": "2"}
    resp = client.post("/call_results", json=payload, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_rate"] == 2000
    assert body["negotiation_rounds"] == 2


def test_metrics_funnel_effectiveness_and_transfer():
    # Booked LD-1001 at 2000 (loadboard 1850, ceiling 2150) with a transfer.
    client.post(
        "/call_results",
        json={
            "load_id": "LD-1001", "outcome": "booked", "sentiment": "positive",
            "final_rate": 2000, "negotiation_rounds": 1, "transferred": "true",
        },
        headers=AUTH,
    )
    m = client.get("/metrics", headers=AUTH).json()

    # Funnel is present and monotonically non-increasing.
    stages = [s["count"] for s in m["funnel"]]
    assert [s["stage"] for s in m["funnel"]] == [
        "Total calls", "Eligible", "Load matched", "Booked",
    ]
    assert stages == sorted(stages, reverse=True)

    # Effectiveness for our booked LD-1001 deal: markup 150, savings 150.
    assert m["avg_markup_over_loadboard"] is not None
    assert m["avg_savings_vs_ceiling"] is not None
    assert 0.0 <= m["avg_gap_captured_pct"] <= 1.0

    # Transfer reflected.
    assert m["transferred"] >= 1
    assert 0.0 <= m["transfer_rate"] <= 1.0


def test_analytics_requires_auth():
    assert client.get("/metrics").status_code == 401
    assert client.post("/call_results", json={"outcome": "abandoned"}).status_code == 401
