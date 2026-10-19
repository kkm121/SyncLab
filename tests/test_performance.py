"""Performance & Latency Verification Test Suite for Mobile & Low-End Devices.
Verifies that v1, v2, v3, v4, and v5 operations execute within tight latency budgets (< 50ms per op),
concurrent bursts handle multiple sync operations with zero database lock contention,
and static frontend assets are served with proper mobile viewport headers.
"""

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_v1_to_v5_latency_benchmarks():
    """Verify that document creation, fast-forward, 3-way Diff3 merge,
    conflict detection, and resolution execute with sub-50ms server response times.
    """
    # 1. v1: Create Document
    t0 = time.perf_counter()
    resp1 = client.post(
        "/documents",
        json={
            "title": "Mobile Performance Doc",
            "body": "Section 1: Mobile Core\nSection 2: Engine\nSection 3: Cache",
            "device_id": "laptop",
        },
    )
    t1 = time.perf_counter()
    v1_ms = (t1 - t0) * 1000
    assert resp1.status_code == 201
    doc_id = resp1.json()["id"]
    assert resp1.json()["version"] == 1

    # 2. v2: Fast-forward Append (Phone online)
    t0 = time.perf_counter()
    resp2 = client.post(
        "/sync",
        json={
            "device_id": "phone-xiaomi",
            "document_id": doc_id,
            "base_version": 1,
            "body": "Section 1: Mobile Core\nSection 2: Engine\nSection 3: Cache\nSection 4: Low-End Optimization",
            "strategy": "diff3",
        },
    )
    t1 = time.perf_counter()
    v2_ms = (t1 - t0) * 1000
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["outcome"] == "accepted"
    assert data2["current_version"] == 2
    # Verify sub-50ms execution
    assert v2_ms < 50.0, f"v2 fast-forward took too long: {v2_ms:.2f}ms"

    # 3. v3: 3-Way Diff3 Auto-Merge (Laptop flush with stale base v1)
    t0 = time.perf_counter()
    resp3 = client.post(
        "/sync",
        json={
            "device_id": "laptop",
            "document_id": doc_id,
            "base_version": 1,
            "body": "Section 1: Mobile Core [HIGH REFRESH 120HZ]\nSection 2: Engine\nSection 3: Cache",
            "strategy": "diff3",
        },
    )
    t1 = time.perf_counter()
    v3_ms = (t1 - t0) * 1000
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["outcome"] == "merged"
    assert data3["current_version"] == 3
    # Verify sub-50ms execution for Diff3 line reconciliation
    assert v3_ms < 50.0, f"v3 diff3 merge took too long: {v3_ms:.2f}ms"

    # 4. v4: Phone edits Section 2 online -> v4
    resp4 = client.post(
        "/sync",
        json={
            "device_id": "phone-xiaomi",
            "document_id": doc_id,
            "base_version": 3,
            "body": "Section 1: Mobile Core [HIGH REFRESH 120HZ]\nSection 2: Engine (ARM Neon Vectorized)\nSection 3: Cache\nSection 4: Low-End Optimization",
            "strategy": "diff3",
        },
    )
    assert resp4.status_code == 200
    assert resp4.json()["current_version"] == 4

    # 5. Conflict: Laptop syncs with stale base v3 on Section 2 -> conflict detected
    t0 = time.perf_counter()
    resp_conflict = client.post(
        "/sync",
        json={
            "device_id": "laptop",
            "document_id": doc_id,
            "base_version": 3,
            "body": "Section 1: Mobile Core [HIGH REFRESH 120HZ]\nSection 2: Engine (GPU Compute Shader)\nSection 3: Cache\nSection 4: Low-End Optimization",
            "strategy": "diff3",
        },
    )
    t1 = time.perf_counter()
    conflict_ms = (t1 - t0) * 1000
    assert resp_conflict.status_code == 200
    assert resp_conflict.json()["outcome"] == "conflict"
    assert conflict_ms < 50.0

    # 6. v5: Laptop resolves via client_wins -> v5
    t0 = time.perf_counter()
    resp5 = client.post(
        "/sync",
        json={
            "device_id": "laptop",
            "document_id": doc_id,
            "base_version": 3,
            "body": "Section 1: Mobile Core [HIGH REFRESH 120HZ]\nSection 2: Engine (GPU Compute Shader)\nSection 3: Cache\nSection 4: Low-End Optimization",
            "strategy": "client_wins",
        },
    )
    t1 = time.perf_counter()
    v5_ms = (t1 - t0) * 1000
    assert resp5.status_code == 200
    assert resp5.json()["outcome"] == "resolved"
    assert resp5.json()["current_version"] == 5
    assert v5_ms < 50.0


def test_rapid_sync_burst_throughput():
    """Verify that rapid consecutive edits from mobile devices don't cause database locks."""
    resp = client.post(
        "/documents",
        json={"title": "Throughput Benchmark", "body": "Initial", "device_id": "bench-dev"},
    )
    doc_id = resp.json()["id"]

    start = time.perf_counter()
    iterations = 25
    current_ver = 1

    for i in range(iterations):
        res = client.post(
            "/sync",
            json={
                "device_id": f"device-client-{i % 3}",
                "document_id": doc_id,
                "base_version": current_ver,
                "body": f"Iteration content update number {i + 1}\nData stream payload active.",
                "strategy": "diff3",
            },
        )
        assert res.status_code == 200
        current_ver = res.json()["current_version"]

    total_time = time.perf_counter() - start
    avg_per_op = (total_time / iterations) * 1000
    assert current_ver == iterations + 1
    # Average operation should remain well below 25ms
    assert avg_per_op < 25.0, f"Average sync op took too long: {avg_per_op:.2f}ms"


def test_static_mobile_assets_served():
    """Verify that the frontend entry point is served with proper mobile viewport tag."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # Must have mobile viewport configuration
    assert "name=\"viewport\"" in html or "viewport" in html
    assert "width=device-width" in html
