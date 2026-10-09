"""SyncLab Real-Time Event Hub
Manages active WebSocket connections, SSE event streams, and event broadcasting.
Provides zero-overhead asynchronous event distribution for multi-device sync.
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import WebSocket

log = logging.getLogger("synclab.realtime")


class RealtimeHub:
    """Singleton event hub for real-time synchronization notifications."""

    def __init__(self, max_history: int = 100):
        self.active_websockets: List[WebSocket] = []
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket subscriber."""
        await websocket.accept()
        self.active_websockets.append(websocket)
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        # Send initial handshake with recent events
        initial_payload = {
            "type": "CONNECTION_ESTABLISHED",
            "timestamp": time.time(),
            "active_clients": len(self.active_websockets),
            "recent_events": self.history[-10:],
        }
        await websocket.send_text(json.dumps(initial_payload))
        log.info(f"WebSocket client connected. Total clients: {len(self.active_websockets)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket subscriber."""
        if websocket in self.active_websockets:
            self.active_websockets.remove(websocket)
            log.info(f"WebSocket client disconnected. Remaining: {len(self.active_websockets)}")

    def record_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Record an event into historical memory buffer."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        self.history.append(event)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        return event

    async def broadcast_async(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast an event to all connected WebSocket clients asynchronously."""
        event = self.record_event(event_type, data)
        payload = json.dumps(event)

        stale_clients = []
        for ws in list(self.active_websockets):
            try:
                await ws.send_text(payload)
            except Exception as e:
                log.warning(f"Failed to send to client: {e}")
                stale_clients.append(ws)

        for ws in stale_clients:
            self.disconnect(ws)

        return event

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous or asynchronous broadcast wrapper."""
        event = self.record_event(event_type, data)
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                asyncio.create_task(self.broadcast_async(event_type, data))
                return event
        except RuntimeError:
            pass

        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.broadcast_async(event_type, data), self._loop)
            except Exception as e:
                log.warning(f"Threadsafe broadcast error: {e}")

        return event

    async def sse_generator(self) -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events for connected HTTP streams."""
        last_idx = len(self.history)
        yield f"data: {json.dumps({'type': 'STREAM_CONNECTED', 'timestamp': time.time()})}\n\n"

        while True:
            await asyncio.sleep(0.5)
            if len(self.history) > last_idx:
                for ev in self.history[last_idx:]:
                    yield f"data: {json.dumps(ev)}\n\n"
                last_idx = len(self.history)


# Global singleton instance
hub = RealtimeHub()
