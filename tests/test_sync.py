"""Tests for core SyncLab synchronization: fast-forward, 3-way merge, conflict detection, tombstones."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_fast_forward_accepted():
    """When client is on current version, non-conflicting change commits cleanly."""
    res = client.post(
        "/documents",
        json={"title": "Doc 1", "body": "Genesis", "device_id": "device-a"},
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    sync_res = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Genesis + Edit 1",
            "device_id": "device-a",
            "strategy": "merge",
        },
    )
    assert sync_res.status_code == 200
    data = sync_res.json()
    assert data["outcome"] == "accepted"
    assert data["current_version"] == 2
    assert data["document"]["body"] == "Genesis + Edit 1"


def test_disjoint_edits_merge():
    """Two offline branches with disjoint line edits merge cleanly via 3-way Diff3."""
    res = client.post(
        "/documents",
        json={
            "title": "Doc Merge",
            "body": "Header\n\nMiddle\n\nFooter",
            "device_id": "laptop",
        },
    )
    doc_id = res.json()["id"]

    # Laptop edits Header (v1 -> v2)
    lap = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "New Header\n\nMiddle\n\nFooter",
            "device_id": "laptop",
            "strategy": "merge",
        },
    )
    assert lap.json()["outcome"] == "accepted"
    assert lap.json()["current_version"] == 2

    # Phone branched from v1 and edits Footer
    phone = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Header\n\nMiddle\n\nNew Footer",
            "device_id": "phone",
            "strategy": "merge",
        },
    )
    assert phone.status_code == 200
    data = phone.json()
    assert data["outcome"] == "merged"
    assert data["current_version"] == 3
    # Both Header and Footer edits preserved
    assert "New Header" in data["document"]["body"]
    assert "New Footer" in data["document"]["body"]


def test_same_field_conflict_never_overwrites():
    """Concurrent edit on the exact same line results in conflict, never silent overwrite."""
    res = client.post(
        "/documents",
        json={"title": "Doc Conflict", "body": "Version One", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    # D1 advances to v2
    client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Version Two by D1",
            "device_id": "d1",
        },
    )

    # D2 tries to advance from v1 with competing text
    sync_res = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "Version Two by D2",
            "device_id": "d2",
            "strategy": "merge",
        },
    )
    data = sync_res.json()
    assert data["outcome"] == "conflict"
    assert len(data["conflicts"]) > 0


def test_base_ahead_rejected():
    """Client sending base_version higher than server is rejected."""
    res = client.post(
        "/documents",
        json={"title": "Doc Future", "body": "Hello", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    sync_res = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 999,
            "body": "Future write",
            "device_id": "d1",
        },
    )
    assert sync_res.json()["outcome"] == "rejected"


def test_unknown_document_404_single_rejected_batch():
    """Unknown document ID returns 404 on single sync."""
    res = client.post(
        "/sync",
        json={"document_id": 999999, "base_version": 1, "body": "Ghost", "device_id": "d1"},
    )
    assert res.status_code == 404


def test_idempotent_replay():
    """Replaying the exact same op_id returns stored outcome without duplicate write."""
    res = client.post(
        "/documents",
        json={"title": "Idempotent Doc", "body": "Base", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    import uuid
    unique_op_id = f"idem-{uuid.uuid4().hex}"
    op = {
        "op_id": unique_op_id,
        "document_id": doc_id,
        "base_version": 1,
        "body": "Updated Body",
        "device_id": "d1",
    }
    r1 = client.post("/sync", json=op).json()
    assert r1["outcome"] == "accepted"
    v1 = r1["current_version"]

    r2 = client.post("/sync", json=op).json()
    assert r2["outcome"] == "idempotent_replay"
    assert r2["current_version"] == v1


def test_tags_union_and_meta_merge():
    """Disjoint metadata and tags merge automatically."""
    res = client.post(
        "/documents",
        json={
            "title": "Meta Doc",
            "body": "Content",
            "tags": ["core"],
            "meta": {"dept": "eng"},
            "device_id": "d1",
        },
    )
    doc_id = res.json()["id"]

    # D1 adds a tag and meta key (v1 -> v2)
    client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "tags": ["core", "infra"],
            "meta": {"dept": "eng", "tier": "p0"},
            "device_id": "d1",
        },
    )

    # D2 concurrent from v1 adds another meta key
    r2 = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "tags": ["core", "backend"],
            "meta": {"dept": "eng", "region": "us-east"},
            "device_id": "d2",
            "strategy": "merge",
        },
    ).json()

    assert r2["outcome"] == "merged"
    doc = r2["document"]
    assert "infra" in doc["tags"] or "backend" in doc["tags"]
    assert "tier" in doc["meta"] or "region" in doc["meta"]


def test_meta_same_key_conflict():
    """Competing values for the exact same metadata key produce conflict."""
    res = client.post(
        "/documents",
        json={"title": "Doc Meta Conflict", "meta": {"owner": "alice"}, "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "meta": {"owner": "bob"}, "device_id": "d1"},
    )

    r2 = client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "meta": {"owner": "charlie"}, "device_id": "d2", "strategy": "merge"},
    ).json()
    assert r2["outcome"] == "conflict"


def test_body_disjoint_lines_merge():
    """3-way line diff merges non-overlapping hunks."""
    initial = "1. First\n2. Second\n3. Third\n4. Fourth\n"
    res = client.post(
        "/documents",
        json={"title": "Line Merge", "body": initial, "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    # Edit line 1
    client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "1. First Modified\n2. Second\n3. Third\n4. Fourth\n",
            "device_id": "d1",
        },
    )

    # Concurrently edit line 4 from base v1
    r2 = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "base_version": 1,
            "body": "1. First\n2. Second\n3. Third\n4. Fourth Modified\n",
            "device_id": "d2",
            "strategy": "merge",
        },
    ).json()

    assert r2["outcome"] == "merged"
    assert "First Modified" in r2["document"]["body"]
    assert "Fourth Modified" in r2["document"]["body"]


def test_tombstone_and_restore():
    """Soft deleted documents record tombstone and can be point-in-time restored."""
    res = client.post(
        "/documents",
        json={"title": "Delete Me", "body": "Valuable Data", "device_id": "d1"},
    )
    doc_id = res.json()["id"]

    # Delete via sync
    del_res = client.post(
        "/sync",
        json={"document_id": doc_id, "base_version": 1, "delete": True, "device_id": "d1"},
    ).json()
    assert del_res["document"]["deleted"] is True

    # Restore past version v1
    rest_res = client.post(f"/documents/{doc_id}/restore/1")
    assert rest_res.status_code == 200
    restored = rest_res.json()
    assert restored["deleted"] is False
    assert restored["body"] == "Valuable Data"
