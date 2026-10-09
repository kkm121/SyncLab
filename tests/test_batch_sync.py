"""Tests for Atomic Transactional Batch Synchronization."""
import pytest
from app.schemas import Strategy, Outcome


def test_batch_sync_atomic_operations(client):
    # 1. Create document 1 and 2
    res1 = client.post("/documents", json={"title": "Doc 1", "body": "Line 1"})
    id1 = res1.json()["id"]
    res2 = client.post("/documents", json={"title": "Doc 2", "body": "Line 1"})
    id2 = res2.json()["id"]

    # 2. Issue a batch sync operation with multiple updates
    batch_payload = {
        "device_id": "test-tablet-01",
        "operations": [
            {
                "document_id": id1,
                "base_version": 1,
                "body": "Line 1\nLine 2 added",
                "device_id": "test-tablet-01",
                "strategy": "merge",
            },
            {
                "document_id": id2,
                "base_version": 1,
                "title": "Doc 2 Renamed",
                "device_id": "test-tablet-01",
                "strategy": "merge",
            },
            {
                "document_id": None,
                "title": "Batch Created Doc",
                "body": "Content from offline queue",
                "device_id": "test-tablet-01",
                "strategy": "merge",
            },
        ],
    }

    # Test /sync/batch (returns list)
    resp = client.post("/sync/batch", json=batch_payload)
    assert resp.status_code == 200
    raw = resp.json()
    results = raw["results"] if isinstance(raw, dict) and "results" in raw else raw
    assert len(results) == 3
    assert results[0]["outcome"] == "accepted"
    assert results[1]["outcome"] == "accepted"
    assert results[2]["outcome"] == "accepted"

    # Test /sync/batch-summary (returns aggregate summary)
    summary_resp = client.post("/sync/batch-summary", json=batch_payload)
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    assert data["total_operations"] == 3
    assert data["accepted_count"] >= 1
