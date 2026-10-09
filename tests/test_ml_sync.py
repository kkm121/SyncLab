"""Tests for SyncLab ML Domain Suite:
1. Semantic Conflict Detection (NLP / Negation & Contradiction)
2. Conflict Risk Prediction & Strategy Recommender (Scikit-Learn Classifier)
3. Smart Merge Synthesis & Linguistic Coherence Scoring
4. Sync Anomaly & Payload Mutation Detector
"""
import pytest
from app.ml.service import (
    SemanticConflictDetector,
    ConflictRiskPredictor,
    SmartMergeSynthesizer,
    SyncAnomalyDetector,
    get_ml_service,
)
from app.schemas import Strategy


def test_semantic_conflict_detector_identifies_logical_contradiction():
    detector = SemanticConflictDetector()
    
    # Non-overlapping disjoint lines that semantically contradict
    base_text = "Conference room reservation is pending approval."
    peer_a_text = "Conference room reservation is confirmed and active for 14:00."
    peer_b_text = "Conference room reservation is cancelled and rejected."
    
    res = detector.detect_semantic_contradiction(base_text, peer_a_text, peer_b_text)
    assert res["has_semantic_conflict"] is True
    assert res["conflict_type"] in ("negation_contradiction", "semantic_divergence")
    assert res["divergence_score"] > 0.35
    assert len(res["contradiction_signals"]) > 0


def test_semantic_conflict_detector_passes_cooperative_edits():
    detector = SemanticConflictDetector()
    
    base_text = "Project Architecture: High-level overview of services."
    peer_a_text = "Project Architecture: High-level overview of services. Added Redis cache layer."
    peer_b_text = "Project Architecture: High-level overview of services. Added PostgreSQL database."
    
    res = detector.detect_semantic_contradiction(base_text, peer_a_text, peer_b_text)
    assert res["has_semantic_conflict"] is False
    assert res["divergence_score"] < 0.65


def test_conflict_risk_predictor_predicts_probability_and_strategy():
    predictor = ConflictRiskPredictor()
    predictor.ensure_trained()
    
    # Low risk edit: small addition, low divergence
    low_risk = predictor.predict_risk(
        lines_changed_a=2,
        lines_changed_b=2,
        levenshtein_ratio=0.92,
        offline_seconds=60,
        ast_type="paragraph",
    )
    assert 0.0 <= low_risk["conflict_probability"] <= 0.45
    assert low_risk["risk_level"] in ("LOW", "NEGLIGIBLE")
    assert low_risk["recommended_strategy"] in (Strategy.merge.value, "ast_merge", "diff3")

    # High risk edit: massive divergence, conflicting sections, long offline drift
    high_risk = predictor.predict_risk(
        lines_changed_a=45,
        lines_changed_b=52,
        levenshtein_ratio=0.25,
        offline_seconds=86400,
        ast_type="root_heading",
    )
    assert high_risk["conflict_probability"] >= 0.50
    assert high_risk["risk_level"] in ("HIGH", "CRITICAL")
    assert high_risk["recommended_strategy"] in (Strategy.manual.value, "crdt", "ast_merge")


def test_smart_merge_synthesizer_ranks_candidates_by_coherence():
    synthesizer = SmartMergeSynthesizer()
    
    conflict_chunk_a = "Deploy backend cluster on AWS us-east-1 with 8 replicas."
    conflict_chunk_b = "Deploy backend cluster on GCP us-central1 with auto-scaling enabled."
    
    candidates = synthesizer.synthesize_resolutions(conflict_chunk_a, conflict_chunk_b)
    assert len(candidates) >= 2
    for cand in candidates:
        assert "merged_text" in cand
        assert "coherence_score" in cand
        assert 0.0 <= cand["coherence_score"] <= 1.0
        assert "strategy_description" in cand


def test_sync_anomaly_detector_flags_corrupted_payload():
    detector = SyncAnomalyDetector()
    
    # Normal payload
    normal_text = "# System Overview\nThis document outlines our offline synchronization pipeline."
    assert detector.is_anomalous(normal_text, lines_changed=3)["is_anomaly"] is False
    
    # Anomaly payload: extreme entropy / random garbage or bomb payload
    anomalous_text = "\x00\x01\xff\xfe\x00" * 400 + "A" * 100000
    res = detector.is_anomalous(anomalous_text, lines_changed=5000)
    assert res["is_anomaly"] is True
    assert "entropy" in res["reason"].lower() or "churn" in res["reason"].lower() or "binary" in res["reason"].lower()


def test_ml_service_endpoint_integration(client):
    ml_svc = get_ml_service()
    assert ml_svc is not None
    
    payload = {
        "base_text": "Meeting room is open.",
        "peer_a_text": "Meeting room is booked and confirmed.",
        "peer_b_text": "Meeting room is closed and cancelled.",
        "lines_changed_a": 1,
        "lines_changed_b": 1,
        "offline_seconds": 300,
    }
    
    resp = client.post("/sync/ml/analyze-conflict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "semantic_analysis" in data
    assert "risk_prediction" in data
    assert "smart_resolutions" in data
    assert data["semantic_analysis"]["has_semantic_conflict"] is True
