"""Tests for cutting-edge SyncLab innovations:
1. FugueMax Sequence CRDT (Maximal Non-Interleaving)
2. Prolly Tree Merkle Set Reconciliation (FastCDC & Probabilistic B-Trees)
3. Structured Markdown AST 3-Way Merge
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.engine.fugue_crdt import FugueCRDT, FugueNode
from app.engine.prolly_tree import ProllyTree, fast_cdc_chunk
from app.engine.structured_ast_merge import structured_markdown_merge

client = TestClient(app)


def test_fuguemax_prevents_interleaving_anomaly():
    """Verify that concurrent typing at the same origin does NOT interleave characters."""
    doc = FugueCRDT()
    # Initial state: "HELLO"
    doc.insert_text(0, "HELLO", client_id="genesis")

    # Client A inserts " WORLD" at index 5
    ops_a = doc.prepare_insert(5, " WORLD", client_id="client_a")

    # Client B concurrently inserts " EVERYONE" at index 5
    ops_b = doc.prepare_insert(5, " EVERYONE", client_id="client_b")

    # Both clients receive each other's operations in opposite orders
    doc_1 = FugueCRDT()
    doc_1.insert_text(0, "HELLO", client_id="genesis")
    doc_1.apply_remote_ops(ops_a)
    doc_1.apply_remote_ops(ops_b)

    doc_2 = FugueCRDT()
    doc_2.insert_text(0, "HELLO", client_id="genesis")
    doc_2.apply_remote_ops(ops_b)
    doc_2.apply_remote_ops(ops_a)

    text_1 = doc_1.get_text()
    text_2 = doc_2.get_text()

    # Convergence (Strong Eventual Consistency)
    assert text_1 == text_2

    # Maximal Non-Interleaving: Characters must not be scrambled together (e.g. no " W EOVRELYDONEE")
    assert "WORLD" in text_1
    assert "EVERYONE" in text_1
    assert ("HELLO WORLD EVERYONE" == text_1) or ("HELLO EVERYONE WORLD" == text_1)


def test_prolly_tree_deterministic_merkle_root():
    """Verify that Prolly Trees generate the exact same Merkle root regardless of insertion order."""
    data_1 = [
        {"id": "doc-1", "title": "Alpha Architecture", "body": "Microservices design spec."},
        {"id": "doc-2", "title": "Beta Protocol", "body": "P2P replication protocol."},
        {"id": "doc-3", "title": "Gamma Telemetry", "body": "Metrics and trace logs."},
    ]

    # Insert in forward order
    tree_1 = ProllyTree()
    for item in data_1:
        tree_1.insert(item["id"], item)

    # Insert in reverse order
    tree_2 = ProllyTree()
    for item in reversed(data_1):
        tree_2.insert(item["id"], item)

    # Deterministic Merkle Root
    assert tree_1.root_hash() == tree_2.root_hash()
    assert len(tree_1.root_hash()) == 64  # SHA-256


def test_prolly_tree_logarithmic_diff_reconciliation():
    """Verify set reconciliation identifies only the modified chunk between two trees."""
    tree_a = ProllyTree()
    tree_b = ProllyTree()

    for i in range(10):
        item = {"id": f"doc-{i}", "val": f"Content item {i}"}
        tree_a.insert(item["id"], item)
        tree_b.insert(item["id"], item)

    # Initially roots match
    assert tree_a.root_hash() == tree_b.root_hash()

    # Mutate a single document on Tree B
    tree_b.insert("doc-4", {"id": "doc-4", "val": "Mutated offline edit"})
    assert tree_a.root_hash() != tree_b.root_hash()

    # Reconcile diff
    diff = tree_a.reconcile_with(tree_b)
    assert "modified_keys" in diff
    assert "doc-4" in diff["modified_keys"]
    assert len(diff["modified_keys"]) == 1


def test_structured_markdown_ast_merge_disjoint_sections():
    """Verify that edits to different Markdown blocks merge cleanly without false conflicts."""
    base_md = (
        "# Engineering Spec\n\n"
        "## Overview\n"
        "This is the initial system architecture.\n\n"
        "## Components\n"
        "- Gateway API\n"
        "- Database Node\n"
    )

    # Side A modifies Overview
    mine_md = (
        "# Engineering Spec\n\n"
        "## Overview\n"
        "This is the updated high-availability system architecture.\n\n"
        "## Components\n"
        "- Gateway API\n"
        "- Database Node\n"
    )

    # Side B appends an item to Components
    theirs_md = (
        "# Engineering Spec\n\n"
        "## Overview\n"
        "This is the initial system architecture.\n\n"
        "## Components\n"
        "- Gateway API\n"
        "- Database Node\n"
        "- Redis Cache Cluster\n"
    )

    merged, conflicts = structured_markdown_merge(base_md, mine_md, theirs_md)
    assert len(conflicts) == 0
    assert "high-availability" in merged
    assert "Redis Cache Cluster" in merged


def test_sync_api_fuguemax_endpoint():
    resp = client.post(
        "/sync/fugue/simulate",
        json={
            "initial_text": "SYSTEM",
            "peer_a_insert": " ALPHA",
            "peer_b_insert": " BETA",
            "cursor_offset": 6,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "converged_text" in data
    assert "ALPHA" in data["converged_text"]
    assert "BETA" in data["converged_text"]
    assert data["is_non_interleaved"] is True
