"""SyncLab — offline-first sync with honest conflicts. No silent overwrites."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .db import init_db
from .routers import devices, documents, sync
from .schemas import ErrorBody

log = logging.getLogger("synclab")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SyncLab",
    description="Offline-first document sync: versioned writes, 3-way merge, explicit outcomes.",
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


from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(sync.router)
app.include_router(devices.router)


@app.get("/health", tags=["meta"])
def health():
    return {"ok": True, "service": "SyncLab", "version": "1.0.0"}
