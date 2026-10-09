"""SyncLab — offline-first sync with honest conflicts. No silent overwrites."""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import devices, documents, realtime, sync
from .schemas import ErrorBody

log = logging.getLogger("synclab")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SyncLab",
    description="Offline-first document sync: versioned writes, 3-way merge, explicit outcomes, and real-time WebSocket fleet feeds.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_handler(_: Request, exc: HTTPException):
    content = (
        exc.detail
        if isinstance(exc.detail, dict)
        else {"error": str(exc.detail), "code": "http_error", "hint": ""}
    )
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorBody(
            error="Request failed validation.",
            code="validation_error",
            hint=f"{'.'.join(str(x) for x in first.get('loc', []))}: {first.get('msg', '')}",
        ).model_dump(),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(sync.router)
app.include_router(realtime.router)
app.include_router(devices.router)

# Mount static web UI assets if built
assets_dir = os.path.join(STATIC_DIR, "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(
        {
            "service": "SyncLab Offline Sync Engine",
            "docs": "/docs",
            "health": "/health",
            "websocket": "/ws/sync",
        }
    )


@app.get("/health", tags=["meta"])
def health():
    return {"ok": True, "service": "SyncLab", "version": "1.0.0"}
