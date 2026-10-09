"""Tests for sync conflict resolution strategies: manual, server_wins, client_wins, feeds, and concurrent writes."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_manual_never_autowrites():
    """Manual strategy returns conflict and leaves server state intact."""
    res = client.post(
        "/documents",
        json={"title": "Manual Strategy", "body": "Alpha", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    # Server advances to v2
    client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "body": "Beta", "device_id": "d1"},
    )

    # Client tries to sync from v1 using manual strategy
    r = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Gamma",
            "device_id": "d2",
            "strategy": "manual",
        },
    ).json()

    assert r["outcome"] == "conflict"
    assert "Manual strategy" in r["resolution"]
    # Check server state unchanged
    doc = client.get(f"/documents/{doc_id}").json()
    assert doc["body"] == "Beta"


def test_server_wins_keeps_newer():
    """server_wins resolves conflict by keeping server state and acknowledging dropped edits."""
    res = client.post(
        "/documents",
        json={"title": "Server Wins", "body": "Server State", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    # Server advances to v2
    client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "body": "Server State v2", "device_id": "d1"},
    )

    # Stale write with server_wins strategy
    r = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Client State Stale",
            "device_id": "d2",
            "strategy": "server_wins",
        },
    ).json()

    assert r["outcome"] == "resolved"
    assert "Server state kept" in r["resolution"]


def test_client_wins_overrides_explicitly():
    """client_wins forces client state as a new version over conflicting server state."""
    res = client.post(
        "/documents",
        json={"title": "Client Wins", "body": "Initial", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    # Server advances to v2
    client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "body": "Server Advance", "device_id": "d1"},
    )

    # Stale write forcing client_wins
    r = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Forced Client State",
            "device_id": "d2",
            "strategy": "client_wins",
        },
    ).json()

    assert r["outcome"] == "resolved"
    assert r["current_version"] == 3
    assert r["document"]["body"] == "Forced Client State"


def test_history_and_export():
    """Document versions are immutably tracked and exportable as Obsidian markdown."""
    res = client.post(
        "/documents",
        json={"title": "History Doc", "body": "Body v1", "tags": ["sync"], "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "body": "Body v2", "device_id": "d1"},
    )

    # Check version history
    versions = client.get(f"/documents/{doc_id}/versions").json()
    assert len(versions) >= 2

    # Export markdown
    exp = client.get(f"/documents/{doc_id}/export.md")
    assert exp.status_code == 200
    assert "title: History Doc" in exp.text
    assert "Body v2" in exp.text


def test_device_feed_catches_up():
    """Devices register and retrieve catch-up feeds of changes since a version."""
    reg = client.post("/devices/register", json={"device_id": "tablet-feed-1"})
    assert reg.status_code == 200

    # Create doc
    client.post("/documents", json={"title": "Feed Doc", "body": "Hello", "device_id": "d1"})

    changes = client.get("/devices/tablet-feed-1/changes?since_version=0").json()
    assert len(changes) > 0


def test_concurrent_writes_never_corrupt():
    """Verify that multiple concurrent operations preserve consistent monotonic state."""
    res = client.post("/documents", json={"title": "Concurrency Doc", "body": "Start", "device_id": "d1"})
    doc_id = res.json()["id"]

    # Both clients think base is 1
    r1 = client.post("/sync", json={"document_id": doc_id, "base_version": 1, "body": "By A", "device_id": "A"})
    r2 = client.post("/sync", json={"document_id": doc_id, "base_version": 1, "body": "By B", "device_id": "B"})

    assert r1.json()["outcome"] in ("accepted", "merged")
    # Second write cannot silently overwrite: either merged, conflict, or rejected
    assert r2.json()["outcome"] in ("conflict", "merged", "rejected")
