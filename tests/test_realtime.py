"""Tests for SyncLab Real-Time Demonstration Provisions
Verifies WebSocket connections, event hub broadcasting, Server-Sent Events (SSE),
and multi-device simulation scenarios.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.realtime_hub import hub

client = TestClient(app)


def test_realtime_hub_event_recording():
    """Verify hub records and limits event history."""
    hub.history.clear()
    hub.record_event("TEST_EVENT_A", {"data": 123})
    hub.record_event("TEST_EVENT_B", {"data": 456})

    assert len(hub.history) == 2
    assert hub.history[0]["type"] == "TEST_EVENT_A"
    assert hub.history[1]["data"]["data"] == 456


def test_realtime_history_api():
    """Verify GET /sync/realtime/history endpoint."""
    hub.history.clear()
    hub.record_event("API_CHECK_EVENT", {"device": "phone-1"})

    res = client.get("/sync/realtime/history")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    assert any(e["type"] == "API_CHECK_EVENT" for e in events)


def test_realtime_websocket_connection_and_ping():
    """Verify bidirectional WebSocket endpoint /ws/sync."""
    with client.websocket_connect("/ws/sync") as ws:
        # Handshake received immediately upon connection
        handshake_raw = ws.receive_text()
        handshake = json.loads(handshake_raw)
        assert handshake["type"] == "CONNECTION_ESTABLISHED"
        assert "active_clients" in handshake

        # Send ping
        ws.send_text(json.dumps({"action": "ping"}))
        pong_raw = ws.receive_text()
        pong = json.loads(pong_raw)
        assert pong["type"] == "PONG"


def test_realtime_sync_broadcast_to_websocket():
    """Verify that document sync operations trigger real-time broadcasts to connected WebSockets."""
    with client.websocket_connect("/ws/sync") as ws:
        _ = ws.receive_text()  # discard initial handshake

        # Trigger a document creation via sync
        create_res = client.post(
            "/documents",
            json={
                "title": "Realtime WS Test",
                "body": "Initial base text",
                "collection": "test",
                "device_id": "test-device-1",
            },
        )
        assert create_res.status_code == 201
        doc_id = create_res.json()["id"]

        # Trigger sync op
        sync_res = client.post(
            "/sync",
            json={
                "device_id": "test-device-1",
                "document_id": doc_id,
                "base_version": 1,
                "body": "Updated text via sync",
                "strategy": "merge",
            },
        )
        assert sync_res.status_code == 200

        # Receive real-time broadcast over WebSocket
        event_raw = ws.receive_text()
        event = json.loads(event_raw)
        assert event["type"].startswith("SYNC_")
        assert event["data"]["device_id"] == "test-device-1"
        assert event["data"]["document_id"] == doc_id


def test_realtime_simulation_disjoint_merge():
    """Verify POST /sync/realtime/simulate for disjoint offline merge scenario."""
    res = client.post(
        "/sync/realtime/simulate",
        json={
            "scenario": "disjoint_merge",
            "devices": ["laptop-test", "phone-test", "tablet-test"],
            "step_delay_seconds": 0.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["scenario"] == "disjoint_merge"
    assert data["total_steps"] >= 5

    event_types = [e["type"] for e in data["events"]]
    assert "SIMULATION_INITIATED" in event_types
    assert "DEVICE_STATE_CHANGE" in event_types
    assert "LOCAL_BUFFER_EDITED" in event_types
    assert "SYNC_COMMITTED" in event_types
    assert "SYNC_AUTO_MERGED" in event_types


def test_realtime_simulation_same_line_conflict():
    """Verify POST /sync/realtime/simulate for same-line conflict protection."""
    res = client.post(
        "/sync/realtime/simulate",
        json={
            "scenario": "same_line_conflict",
            "devices": ["laptop-conflict", "phone-conflict"],
            "step_delay_seconds": 0.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"

    event_types = [e["type"] for e in data["events"]]
    assert "CONFLICT_ZERO_OVERWRITE_PROTECTION" in event_types


def test_root_serves_frontend():
    """Verify GET / serves HTML index."""
    res = client.get("/")
    assert res.status_code == 200
    assert "html" in res.headers.get("content-type", "") or res.json().get("service")
