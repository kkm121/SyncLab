"""Sync entry points: single op, batch queue flush, FugueMax CRDT, Prolly Tree,
AST merge, Vector Clocks, and ML Semantic Conflict Detection.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import (
    ASTMergeIn,
    ASTMergeOut,
    BatchSyncRequest,
    BatchSyncResponse,
    ErrorBody,
    FugueSimulateIn,
    FugueSimulateOut,
    MLConflictAnalysisRequest,
    MLConflictAnalysisResponse,
    Outcome,
    ProllyReconcileIn,
    ProllyReconcileOut,
    SyncOp,
    SyncResult,
    VectorClockCompareRequest,
    VectorClockCompareResponse,
)
from ..sync_service import execute_op
from ..engine.fugue_crdt import FugueCRDT
from ..engine.prolly_tree import ProllyTree
from ..engine.structured_ast_merge import structured_markdown_merge
from ..engine.vector_clock import VectorClock, CausalRelation
from ..ml.service import get_ml_service

router = APIRouter(tags=["sync"])


@router.post("/sync", response_model=SyncResult)
def sync_once(op: SyncOp, db: Session = Depends(get_db)):
    result = execute_op(db, op)
    if (
        result.outcome == Outcome.rejected
        and result.document is None
        and "Unknown document" in (result.resolution or "")
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                error=result.resolution or "Unknown document.",
                code="unknown_document",
            ).model_dump(),
        )
    return result


@router.post("/sync/batch", response_model=BatchSyncResponse)
def sync_batch(batch: BatchSyncRequest, db: Session = Depends(get_db)):
    """Atomic multi-op batch sync for offline device reconnection."""
    results = [execute_op(db, op) for op in batch.operations]
    accepted = sum(
        1 for r in results if r.outcome in (Outcome.accepted, Outcome.merged, Outcome.resolved)
    )
    conflicts = sum(1 for r in results if r.outcome == Outcome.conflict)
    rejected = sum(1 for r in results if r.outcome == Outcome.rejected)
    return BatchSyncResponse(
        total_operations=len(results),
        accepted_count=accepted,
        conflict_count=conflicts,
        rejected_count=rejected,
        results=results,
    )


@router.post("/sync/batch-summary", response_model=BatchSyncResponse)
def sync_batch_summary(batch: BatchSyncRequest, db: Session = Depends(get_db)):
    """Aggregate summary of batch sync operations."""
    return sync_batch(batch, db)


@router.post("/sync/vector-clock/compare", response_model=VectorClockCompareResponse)
def compare_vector_clocks(body: VectorClockCompareRequest):
    """Compares two vector clocks to determine causal ordering (ANCESTOR, DESCENDANT, IDENTICAL, CONCURRENT)."""
    vc_a = VectorClock(body.clock_a)
    vc_b = VectorClock(body.clock_b)
    relation = vc_a.compare(vc_b)
    merged = vc_a.merge(vc_b)
    explanations = {
        CausalRelation.IDENTICAL: "Both devices are identical and at the exact same causal state.",
        CausalRelation.ANCESTOR: "Clock A is a direct causal ancestor of Clock B (Clock A happened before B).",
        CausalRelation.DESCENDANT: "Clock A is a causal descendant of Clock B (Clock B happened before A).",
        CausalRelation.CONCURRENT: "Independent concurrent offline branches detected! Conflict resolution required.",
    }
    return VectorClockCompareResponse(
        relation=relation.value,
        merged_clock=merged.to_dict(),
        explanation=explanations[relation],
    )


@router.post("/sync/ml/analyze-conflict", response_model=MLConflictAnalysisResponse)
def analyze_conflict_with_ml(body: MLConflictAnalysisRequest):
    """Analyzes concurrent edits with ML: semantic contradiction detection, conflict risk scoring, and smart synthesis."""
    ml_svc = get_ml_service()

    # 1. Semantic contradiction analysis
    semantic = ml_svc.conflict_detector.detect_semantic_contradiction(
        body.base_text, body.peer_a_text, body.peer_b_text
    )

    # 2. Risk prediction
    len_a = len(body.peer_a_text)
    len_b = len(body.peer_b_text)
    lev_ratio = 1.0 - (abs(len_a - len_b) / max(1, max(len_a, len_b)))
    risk = ml_svc.risk_predictor.predict_risk(
        body.lines_changed_a,
        body.lines_changed_b,
        lev_ratio,
        body.offline_seconds,
        body.ast_type,
    )

    # 3. Smart resolution synthesis
    resolutions = ml_svc.synthesizer.synthesize_resolutions(body.peer_a_text, body.peer_b_text)

    # 4. Anomaly detector
    combined = f"{body.peer_a_text}\n{body.peer_b_text}"
    anomaly = ml_svc.anomaly_detector.is_anomalous(
        combined, body.lines_changed_a + body.lines_changed_b
    )

    return MLConflictAnalysisResponse(
        semantic_analysis=semantic,
        risk_prediction=risk,
        smart_resolutions=resolutions,
        anomaly_status=anomaly,
    )


@router.post("/sync/fugue/simulate", response_model=FugueSimulateOut)
def simulate_fugue_merge(body: FugueSimulateIn):
    """Simulates concurrent typing with the FugueMax CRDT algorithm (Weidner & Kleppmann 2025)."""
    base_doc = FugueCRDT()
    if body.initial_text:
        base_doc.insert_text(0, body.initial_text, client_id="genesis")

    offset = min(body.cursor_offset, len(body.initial_text))

    # Prepare operations for Client A and Client B concurrently
    ops_a = base_doc.prepare_insert(offset, body.peer_a_insert, client_id="client_a")
    ops_b = base_doc.prepare_insert(offset, body.peer_b_insert, client_id="client_b")

    # Apply both to converge
    peer_a_doc = FugueCRDT()
    if body.initial_text:
        peer_a_doc.insert_text(0, body.initial_text, client_id="genesis")
    peer_a_doc.apply_remote_ops(ops_a)
    peer_a_text = peer_a_doc.get_text()

    peer_b_doc = FugueCRDT()
    if body.initial_text:
        peer_b_doc.insert_text(0, body.initial_text, client_id="genesis")
    peer_b_doc.apply_remote_ops(ops_b)
    peer_b_text = peer_b_doc.get_text()

    # Reconciled document (Client A receives B's ops)
    converged_doc = peer_a_doc
    converged_doc.apply_remote_ops(ops_b)
    converged_text = converged_doc.get_text()

    # Verify non-interleaving
    is_non_interleaved = (
        body.peer_a_insert in converged_text and body.peer_b_insert in converged_text
    )

    return FugueSimulateOut(
        converged_text=converged_text,
        is_non_interleaved=is_non_interleaved,
        peer_a_text=peer_a_text,
        peer_b_text=peer_b_text,
        op_count=len(ops_a) + len(ops_b),
        algorithm="FugueMax-TPDS-2025",
    )


@router.post("/sync/prolly/reconcile", response_model=ProllyReconcileOut)
def reconcile_prolly_trees(body: ProllyReconcileIn):
    """Reconciles two document sets using Prolly Tree Merkle Search Tree diffing."""
    tree_local = ProllyTree()
    for item in body.local_items:
        key = str(item.get("id") or item.get("key") or hash(str(item)))
        tree_local.insert(key, item)

    tree_remote = ProllyTree()
    for item in body.remote_items:
        key = str(item.get("id") or item.get("key") or hash(str(item)))
        tree_remote.insert(key, item)

    res = tree_local.reconcile_with(tree_remote)
    return ProllyReconcileOut(**res)


@router.post("/sync/ast-merge", response_model=ASTMergeOut)
def merge_markdown_ast(body: ASTMergeIn):
    """Performs semantic 3-way AST merge across Markdown blocks (Spork / Mergiraf style)."""
    merged, conflicts = structured_markdown_merge(
        body.base_markdown, body.mine_markdown, body.theirs_markdown
    )
    return ASTMergeOut(
        merged_markdown=merged,
        conflict_count=len(conflicts),
        conflicts=conflicts,
    )
