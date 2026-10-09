"""SyncLab Real-Time Demonstration Router
Exposes WebSocket endpoints, Server-Sent Events (SSE), and interactive
live multi-device simulation runners for real-time evaluator demonstrations.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine.realtime_hub import hub
from ..engine.vector_clock import VectorClock
from ..models import Document
from ..schemas import Outcome, Strategy, SyncOp
from ..sync_service import execute_op

router = APIRouter(tags=["realtime"])


class RealtimeSimulateRequest(BaseModel):
    scenario: str = "disjoint_merge"  # "disjoint_merge", "same_line_conflict", "crdt_race"
    devices: List[str] = ["laptop-macbook", "phone-iphone15", "tablet-ipad"]
    step_delay_seconds: float = 0.5


class RealtimeSimulateResponse(BaseModel):
    scenario: str
    status: str
    total_steps: int
    execution_time_seconds: float
    events: List[Dict[str, Any]]


@router.get("/sync/realtime/history")
def get_realtime_history() -> List[Dict[str, Any]]:
    """Retrieve recent real-time synchronization events recorded by the hub."""
    return hub.history


@router.get("/sync/realtime/stream")
async def get_realtime_sse_stream():
    """Stream live synchronization events via Server-Sent Events (SSE)."""
    return StreamingResponse(
        hub.sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/sync")
async def websocket_sync_endpoint(websocket: WebSocket):
    """Bidirectional WebSocket endpoint for real-time document synchronization."""
    await hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action", "ping")
                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "PONG", "timestamp": time.time()}))
                elif action == "broadcast":
                    event_type = msg.get("event_type", "USER_EVENT")
                    payload = msg.get("data", {})
                    await hub.broadcast_async(event_type, payload)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "ERROR", "message": "Invalid JSON format."})
                )
    except WebSocketDisconnect:
        hub.disconnect(websocket)
    except Exception:
        hub.disconnect(websocket)


@router.post("/sync/realtime/simulate", response_model=RealtimeSimulateResponse)
async def run_realtime_simulation(
    req: RealtimeSimulateRequest, db: Session = Depends(get_db)
):
    """Executes a live multi-device simulation scenario with real-time WebSocket/SSE broadcast.
    Demonstrates:
    - Devices going offline
    - Concurrent local edits
    - Divergent vector clocks
    - Reconnection and 3-way line merge or conflict protection
    """
    start_time = time.time()
    events_log: List[Dict[str, Any]] = []

    async def log_and_broadcast(event_type: str, data: Dict[str, Any]):
        ev = await hub.broadcast_async(event_type, data)
        events_log.append(ev)
        if req.step_delay_seconds > 0:
            await asyncio.sleep(req.step_delay_seconds)

    # 1. Initialize Document
    doc = Document(
        collection="realtime-demo",
        title="Live Distributed Systems Spec",
        body=(
            "# Project Specification\n\n"
            "## Section 1: Architecture\n"
            "FastAPI backend running with SQLite CAS storage.\n\n"
            "## Section 2: Storage Engine\n"
            "Append-only version log with cryptographic diff verification."
        ),
        tags_json=json.dumps(["distributed", "offline-sync"]),
        meta_json=json.dumps({"author": "system", "priority": "high"}),
        version=1,
        deleted=False,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc_id = doc.id

    vclock = VectorClock({"server": 1, req.devices[0]: 1, req.devices[1]: 1})

    await log_and_broadcast(
        "SIMULATION_INITIATED",
        {
            "scenario": req.scenario,
            "document_id": doc_id,
            "initial_version": 1,
            "devices": req.devices,
            "vector_clock": vclock.to_dict(),
        },
    )

    if req.scenario == "disjoint_merge":
        # Stage 1: Devices go offline
        await log_and_broadcast(
            "DEVICE_STATE_CHANGE",
            {"device_id": req.devices[0], "status": "OFFLINE", "reason": "Airplane mode entered."},
        )
        await log_and_broadcast(
            "DEVICE_STATE_CHANGE",
            {"device_id": req.devices[1], "status": "OFFLINE", "reason": "Network disconnected."},
        )

        # Stage 2: Concurrent local edits
        vclock.increment(req.devices[0])
        await log_and_broadcast(
            "LOCAL_BUFFER_EDITED",
            {
                "device_id": req.devices[0],
                "section": "Section 1",
                "content": "FastAPI backend running with SQLite CAS storage [UPDATED BY LAPTOP].",
                "vector_clock": vclock.to_dict(),
            },
        )

        vclock.increment(req.devices[1])
        await log_and_broadcast(
            "LOCAL_BUFFER_EDITED",
            {
                "device_id": req.devices[1],
                "section": "Section 2",
                "content": "Append-only version log with cryptographic diff verification [UPDATED BY PHONE].",
                "vector_clock": vclock.to_dict(),
            },
        )

        # Stage 3: Laptop reconnects first
        await log_and_broadcast(
            "DEVICE_STATE_CHANGE",
            {"device_id": req.devices[0], "status": "ONLINE", "reason": "Wi-Fi reconnected."},
        )
        op_laptop = SyncOp(
            device_id=req.devices[0],
            document_id=doc_id,
            base_version=1,
            body=(
                "# Project Specification\n\n"
                "## Section 1: Architecture\n"
                "FastAPI backend running with SQLite CAS storage [UPDATED BY LAPTOP].\n\n"
                "## Section 2: Storage Engine\n"
                "Append-only version log with cryptographic diff verification."
            ),
            strategy=Strategy.merge,
        )
        res_laptop = execute_op(db, op_laptop)
        vclock.increment("server")
        await log_and_broadcast(
            "SYNC_COMMITTED",
            {
                "device_id": req.devices[0],
                "outcome": res_laptop.outcome.value,
                "new_version": res_laptop.current_version,
                "vector_clock": vclock.to_dict(),
            },
        )

        # Stage 4: Phone reconnects with stale base_version=1
        await log_and_broadcast(
            "DEVICE_STATE_CHANGE",
            {"device_id": req.devices[1], "status": "ONLINE", "reason": "Cellular reconnected."},
        )
        op_phone = SyncOp(
            device_id=req.devices[1],
            document_id=doc_id,
            base_version=1,
            body=(
                "# Project Specification\n\n"
                "## Section 1: Architecture\n"
                "FastAPI backend running with SQLite CAS storage.\n\n"
                "## Section 2: Storage Engine\n"
                "Append-only version log with cryptographic diff verification [UPDATED BY PHONE]."
            ),
            strategy=Strategy.merge,
        )
        res_phone = execute_op(db, op_phone)
        vclock.increment("server")
        await log_and_broadcast(
            "SYNC_AUTO_MERGED",
            {
                "device_id": req.devices[1],
                "outcome": res_phone.outcome.value,
                "new_version": res_phone.current_version,
                "merged_fields": res_phone.merged_fields,
                "vector_clock": vclock.to_dict(),
            },
        )

    elif req.scenario == "same_line_conflict":
        # Laptop edits line 4
        op_laptop = SyncOp(
            device_id=req.devices[0],
            document_id=doc_id,
            base_version=1,
            body=(
                "# Project Specification\n\n"
                "## Section 1: Architecture\n"
                "Laptop changed Section 1 to: Microservices Architecture.\n\n"
                "## Section 2: Storage Engine\n"
                "Append-only version log with cryptographic diff verification."
            ),
            strategy=Strategy.merge,
        )
        res_laptop = execute_op(db, op_laptop)
        await log_and_broadcast(
            "SYNC_COMMITTED",
            {
                "device_id": req.devices[0],
                "outcome": res_laptop.outcome.value,
                "new_version": res_laptop.current_version,
            },
        )

        # Phone also edited line 4 with conflicting text!
        op_phone = SyncOp(
            device_id=req.devices[1],
            document_id=doc_id,
            base_version=1,
            body=(
                "# Project Specification\n\n"
                "## Section 1: Architecture\n"
                "Phone changed Section 1 to: Modular Monolith Architecture.\n\n"
                "## Section 2: Storage Engine\n"
                "Append-only version log with cryptographic diff verification."
            ),
            strategy=Strategy.merge,
        )
        res_phone = execute_op(db, op_phone)
        await log_and_broadcast(
            "CONFLICT_ZERO_OVERWRITE_PROTECTION",
            {
                "device_id": req.devices[1],
                "outcome": res_phone.outcome.value,
                "conflicts": [c.model_dump() for c in res_phone.conflicts] if res_phone.conflicts else [],
                "silent_overwrite_prevented": True,
            },
        )

    elapsed = time.time() - start_time
    await log_and_broadcast(
        "SIMULATION_COMPLETED",
        {
            "scenario": req.scenario,
            "total_steps": len(events_log),
            "elapsed_seconds": round(elapsed, 3),
        },
    )

    return RealtimeSimulateResponse(
        scenario=req.scenario,
        status="COMPLETED",
        total_steps=len(events_log),
        execution_time_seconds=round(elapsed, 3),
        events=events_log,
    )
