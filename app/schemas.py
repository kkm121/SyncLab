"""Pydantic schemas for documents, sync ops, results, and errors."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Strategy(str, Enum):
    merge = "merge"
    diff3 = "diff3"
    server_wins = "server_wins"
    client_wins = "client_wins"
    manual = "manual"


class Outcome(str, Enum):
    accepted = "accepted"
    merged = "merged"
    resolved = "resolved"
    conflict = "conflict"
    rejected = "rejected"
    idempotent_replay = "idempotent_replay"


class ErrorBody(BaseModel):
    error: str
    code: str
    hint: str = ""


class DocumentOut(BaseModel):
    id: int
    collection: str
    title: str
    body: str
    tags: list[str]
    meta: dict
    version: int
    deleted: bool
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    collection: str = Field(default="notes", max_length=64)
    title: str = Field(default="", max_length=512)
    body: str = Field(default="", max_length=200_000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    meta: dict = Field(default_factory=dict)
    device_id: str = Field(default="device-default", min_length=1, max_length=64)


class SyncOp(BaseModel):
    document_id: int | None = Field(
        default=None, description="Omit to create a new document."
    )
    collection: str = Field(default="notes", max_length=64)
    title: str | None = Field(default=None, max_length=512)
    body: str | None = Field(default=None, max_length=200_000)
    tags: list[str] | None = Field(default=None, max_length=50)
    meta: dict | None = None
    delete: bool = False
    base_version: int = 0
    device_id: str = Field(min_length=1, max_length=64)
    op_id: str | None = Field(
        default=None, max_length=128, description="Idempotency key."
    )
    strategy: Strategy = Strategy.merge


class ConflictOut(BaseModel):
    field: str
    base: object = None
    mine: object = None
    current: object = None


class SyncResult(BaseModel):
    outcome: Outcome
    document: DocumentOut | None
    base_version: int
    current_version: int
    merged_fields: list[str] = []
    conflicts: list[ConflictOut] = []
    resolution: str = ""


class BatchSyncIn(BaseModel):
    operations: list[SyncOp] = Field(min_length=1, max_length=100)


class DeviceRegister(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    name: str = Field(default="", max_length=128)


class ChangeFeedItem(BaseModel):
    seq: int
    document_id: int
    version: int
    device_id: str
    outcome: str
    deleted: bool
    updated_at: datetime


class VersionOut(BaseModel):
    version: int
    title: str
    body: str
    tags: list[str]
    meta: dict
    deleted: bool
    device_id: str
    strategy: str
    outcome: str
    created_at: datetime

from typing import Any


class ASTMergeIn(BaseModel):
    base_markdown: str
    mine_markdown: str
    theirs_markdown: str


class ASTMergeOut(BaseModel):
    merged_markdown: str
    conflict_count: int
    conflicts: list[dict[str, Any]] = []


class BatchSyncRequest(BaseModel):
    operations: list[SyncOp] = Field(min_length=1, max_length=100)


class BatchSyncResponse(BaseModel):
    total_operations: int
    accepted_count: int
    conflict_count: int
    rejected_count: int
    results: list[SyncResult] = []


class FugueSimulateIn(BaseModel):
    initial_text: str = ""
    peer_a_insert: str = ""
    peer_b_insert: str = ""
    cursor_offset: int = 0


class FugueSimulateOut(BaseModel):
    converged_text: str
    is_non_interleaved: bool
    peer_a_text: str
    peer_b_text: str
    op_count: int
    algorithm: str = "FugueMax-TPDS-2025"


class ProllyReconcileIn(BaseModel):
    local_items: list[dict[str, Any]] = []
    remote_items: list[dict[str, Any]] = []


class ProllyReconcileOut(BaseModel):
    in_sync: bool = False
    local_root: str = ""
    remote_root: str = ""
    modified_keys: list[str] = []
    added_keys: list[str] = []
    removed_keys: list[str] = []
    divergent_count: int = 0
    algorithm: str = "FastCDC-Prolly-Tree"


class VectorClockCompareRequest(BaseModel):
    clock_a: dict[str, int]
    clock_b: dict[str, int]
    node_id: str | None = None


class VectorClockCompareResponse(BaseModel):
    relation: str
    merged_clock: dict[str, int]
    explanation: str


class MLConflictAnalysisRequest(BaseModel):
    base_text: str
    peer_a_text: str
    peer_b_text: str
    lines_changed_a: int = 0
    lines_changed_b: int = 0
    offline_seconds: float = 0.0
    ast_type: str = "text"


class MLConflictAnalysisResponse(BaseModel):
    semantic_analysis: dict[str, Any]
    risk_prediction: dict[str, Any]
    smart_resolutions: list[dict[str, Any]] = []
    anomaly_status: dict[str, Any]
