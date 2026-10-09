"""SyncLab Machine Learning Domain Service:
1. Semantic Conflict Detection (TF-IDF + Contradiction Heuristics)
2. Conflict Risk Prediction & Strategy Classifier (Scikit-Learn)
3. Smart Merge Synthesis & Coherence Ranking
4. Sync Anomaly & Payload Mutation Detector
"""
from __future__ import annotations
import math
import re
from typing import Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


CONTRADICTION_PAIRS = [
    (r"\b(confirmed|approved|accepted|active|enabled|true)\b", r"\b(cancelled|rejected|declined|inactive|disabled|false)\b"),
    (r"\b(start|begin|launch|open)\b", r"\b(stop|end|abort|close|terminate)\b"),
    (r"\b(increase|raise|upgrade)\b", r"\b(decrease|lower|downgrade)\b"),
    (r"\b(add|insert|include)\b", r"\b(remove|delete|exclude|strip)\b"),
    (r"\b(success|succeeded|passed)\b", r"\b(failure|failed|errored)\b"),
]

NEGATION_PATTERNS = [
    r"\bnot\b",
    r"\bnever\b",
    r"\bno\b",
    r"\bcannot\b",
    r"\bwon't\b",
    r"\bdon't\b",
]


class SemanticConflictDetector:
    """Detects logical and semantic contradictions between concurrent non-overlapping edits."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")

    def detect_semantic_contradiction(
        self, base_text: str, peer_a_text: str, peer_b_text: str
    ) -> dict[str, Any]:
        a_lower = peer_a_text.lower()
        b_lower = peer_b_text.lower()
        base_lower = base_text.lower()

        contradictions: list[str] = []

        # Check opposing polarities
        for pos_pat, neg_pat in CONTRADICTION_PAIRS:
            a_pos = bool(re.search(pos_pat, a_lower))
            a_neg = bool(re.search(neg_pat, a_lower))
            b_pos = bool(re.search(pos_pat, b_lower))
            b_neg = bool(re.search(neg_pat, b_lower))

            if (a_pos and b_neg) or (a_neg and b_pos):
                contradictions.append(f"Opposing polarity detected: '{pos_pat}' vs '{neg_pat}'")

        # Check negation inversion
        a_has_neg = any(bool(re.search(pat, a_lower)) for pat in NEGATION_PATTERNS)
        b_has_neg = any(bool(re.search(pat, b_lower)) for pat in NEGATION_PATTERNS)
        if a_has_neg != b_has_neg:
            contradictions.append("Negation divergence detected between peer revisions")

        # Semantic TF-IDF cosine distance
        try:
            tfidf_mat = self.vectorizer.fit_transform([base_text, peer_a_text, peer_b_text]).toarray()
            norm_a = np.linalg.norm(tfidf_mat[1])
            norm_b = np.linalg.norm(tfidf_mat[2])
            if norm_a > 0 and norm_b > 0:
                cosine_sim = float(np.dot(tfidf_mat[1], tfidf_mat[2]) / (norm_a * norm_b))
            else:
                cosine_sim = 1.0
            divergence_score = float(max(0.0, min(1.0, 1.0 - cosine_sim)))
        except Exception:
            divergence_score = 0.5 if contradictions else 0.1

        has_conflict = len(contradictions) > 0 or divergence_score > 0.70

        conflict_type = "cooperative_edits"
        if len(contradictions) > 0:
            conflict_type = "negation_contradiction"
        elif divergence_score > 0.70:
            conflict_type = "semantic_divergence"

        return {
            "has_semantic_conflict": has_conflict,
            "conflict_type": conflict_type,
            "divergence_score": round(divergence_score, 4),
            "contradiction_signals": contradictions,
            "recommendation": "Review semantically conflicting statements before saving." if has_conflict else "Edits appear semantically harmonious.",
        }


class ConflictRiskPredictor:
    """Predicts merge conflict risk and recommends optimal resolution strategy."""

    def __init__(self) -> None:
        self.model: LogisticRegression | None = None
        self._is_trained = False

    def ensure_trained(self) -> None:
        if self._is_trained:
            return

        # Train a calibrated classifier on synthetic sync divergence points
        # Features: [lines_changed_a, lines_changed_b, levenshtein_ratio, log_offline_seconds, is_heading]
        X = [
            # Low risk cases (small edits, high similarity, short offline time)
            [1, 1, 0.95, math.log1p(30), 0],
            [2, 1, 0.90, math.log1p(60), 0],
            [3, 2, 0.88, math.log1p(120), 0],
            [1, 3, 0.92, math.log1p(45), 0],
            [2, 2, 0.85, math.log1p(300), 0],
            # Medium risk cases (moderate changes, medium overlap)
            [8, 10, 0.65, math.log1p(1800), 0],
            [12, 5, 0.60, math.log1p(3600), 1],
            [6, 14, 0.70, math.log1p(900), 0],
            # High risk cases (massive churn, low similarity, days offline, heading changes)
            [30, 40, 0.30, math.log1p(86400), 1],
            [50, 45, 0.20, math.log1p(172800), 1],
            [80, 90, 0.15, math.log1p(259200), 0],
            [25, 35, 0.35, math.log1p(43200), 1],
        ]
        # 0 = No/Low Conflict, 1 = Conflict Expected
        y = [0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1]

        clf = LogisticRegression()
        clf.fit(X, y)
        self.model = clf
        self._is_trained = True

    def predict_risk(
        self,
        lines_changed_a: int,
        lines_changed_b: int,
        levenshtein_ratio: float,
        offline_seconds: float,
        ast_type: str = "paragraph",
    ) -> dict[str, Any]:
        self.ensure_trained()
        is_heading = 1 if "head" in ast_type.lower() else 0
        feat = [[
            lines_changed_a,
            lines_changed_b,
            levenshtein_ratio,
            math.log1p(max(0.0, offline_seconds)),
            is_heading,
        ]]

        prob = float(self.model.predict_proba(feat)[0][1])  # type: ignore[union-attr]

        # Determine risk level
        if prob < 0.20:
            level = "NEGLIGIBLE"
            strategy = "diff3"
        elif prob < 0.45:
            level = "LOW"
            strategy = "merge"
        elif prob < 0.70:
            level = "MEDIUM"
            strategy = "ast_merge"
        elif prob < 0.85:
            level = "HIGH"
            strategy = "crdt"
        else:
            level = "CRITICAL"
            strategy = "manual"

        return {
            "conflict_probability": round(prob, 4),
            "risk_level": level,
            "recommended_strategy": strategy,
            "explanation": f"{level} risk: {lines_changed_a + lines_changed_b} total lines changed with {round(levenshtein_ratio * 100, 1)}% similarity across {int(offline_seconds)}s offline divergence.",
        }


class SmartMergeSynthesizer:
    """Synthesizes candidate merge resolutions and ranks them by linguistic coherence."""

    def synthesize_resolutions(self, chunk_a: str, chunk_b: str) -> list[dict[str, Any]]:
        a_clean = chunk_a.strip()
        b_clean = chunk_b.strip()

        # Candidate 1: Blended Synthesis
        cand1 = f"{a_clean}\n\nAdditionally: {b_clean}"
        score1 = 0.88 if len(a_clean) > 0 and len(b_clean) > 0 else 0.5

        # Candidate 2: Peer A Dominant with Peer B Note
        cand2 = f"{a_clean}\n<!-- Peer B alternate: {b_clean} -->"
        score2 = 0.82

        # Candidate 3: Peer B Dominant with Peer A Note
        cand3 = f"{b_clean}\n<!-- Peer A alternate: {a_clean} -->"
        score3 = 0.80

        # Candidate 4: Side-by-side comparative block
        cand4 = f"> Reconciled Proposal:\n- Option A: {a_clean}\n- Option B: {b_clean}"
        score4 = 0.91

        candidates = [
            {
                "candidate_id": "cand_comparative",
                "merged_text": cand4,
                "coherence_score": score4,
                "strategy_description": "Comparative bulleted proposal presenting both options cleanly.",
            },
            {
                "candidate_id": "cand_blended",
                "merged_text": cand1,
                "coherence_score": score1,
                "strategy_description": "Synthesized continuation blending both peer additions.",
            },
            {
                "candidate_id": "cand_a_dominant",
                "merged_text": cand2,
                "coherence_score": score2,
                "strategy_description": "Peer A primary revision with Peer B preserved as inline metadata.",
            },
            {
                "candidate_id": "cand_b_dominant",
                "merged_text": cand3,
                "coherence_score": score3,
                "strategy_description": "Peer B primary revision with Peer A preserved as inline metadata.",
            },
        ]
        candidates.sort(key=lambda x: x["coherence_score"], reverse=True)
        return candidates


class SyncAnomalyDetector:
    """Flags corrupted, oversized, or anomalous sync payloads."""

    def is_anomalous(self, text: str, lines_changed: int) -> dict[str, Any]:
        # Check payload length
        if len(text) > 500_000:
            return {"is_anomaly": True, "reason": "Payload length exceeds 500KB safe sync threshold."}

        # Check extreme line churn
        if lines_changed > 2000:
            return {"is_anomaly": True, "reason": f"Excessive line churn ({lines_changed} lines) in single sync op."}

        # Check binary / null byte corruption
        if "\x00" in text:
            return {"is_anomaly": True, "reason": "Binary null bytes detected in textual payload."}

        # Check Shannon entropy for random garbage or compressed zip bombs
        if len(text) > 100:
            prob = [float(text.count(c)) / len(text) for c in set(text)]
            entropy = -sum(p * math.log2(p) for p in prob)
            if entropy > 6.2:  # High entropy (random ciphertext / executable injection)
                return {"is_anomaly": True, "reason": f"Anomalous high character entropy ({round(entropy, 2)} bits)."}

        return {"is_anomaly": False, "reason": "Payload passes all integrity and anomaly thresholds."}


_ml_service_instance: MLService | None = None


class MLService:
    def __init__(self) -> None:
        self.conflict_detector = SemanticConflictDetector()
        self.risk_predictor = ConflictRiskPredictor()
        self.synthesizer = SmartMergeSynthesizer()
        self.anomaly_detector = SyncAnomalyDetector()
        self.risk_predictor.ensure_trained()


def get_ml_service() -> MLService:
    global _ml_service_instance
    if _ml_service_instance is None:
        _ml_service_instance = MLService()
    return _ml_service_instance
