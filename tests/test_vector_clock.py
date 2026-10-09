"""Tests for SyncLab Vector Clock & Decentralized Causal Ordering."""
import pytest
from app.engine.vector_clock import VectorClock, CausalRelation


def test_vector_clock_initialization_and_increment():
    vc = VectorClock({"laptop": 1, "phone": 2})
    assert vc.get("laptop") == 1
    assert vc.get("phone") == 2
    assert vc.get("tablet") == 0
    
    vc.increment("laptop")
    assert vc.get("laptop") == 2


def test_vector_clock_causal_relationships():
    # Ancestor vs Descendant
    vc_base = VectorClock({"A": 1, "B": 1})
    vc_desc = VectorClock({"A": 2, "B": 1})
    
    assert vc_base.compare(vc_desc) == CausalRelation.ANCESTOR
    assert vc_desc.compare(vc_base) == CausalRelation.DESCENDANT
    
    # Identical
    vc_copy = VectorClock({"A": 1, "B": 1})
    assert vc_base.compare(vc_copy) == CausalRelation.IDENTICAL
    
    # Concurrent (Forked)
    vc_fork1 = VectorClock({"A": 2, "B": 1})
    vc_fork2 = VectorClock({"A": 1, "B": 2})
    assert vc_fork1.compare(vc_fork2) == CausalRelation.CONCURRENT
    assert vc_fork2.compare(vc_fork1) == CausalRelation.CONCURRENT


def test_vector_clock_merge():
    vc1 = VectorClock({"A": 3, "B": 1, "C": 2})
    vc2 = VectorClock({"A": 1, "B": 4, "D": 1})
    
    merged = vc1.merge(vc2)
    assert merged.clock == {"A": 3, "B": 4, "C": 2, "D": 1}


def test_vector_clock_api_endpoint(client):
    payload = {
        "clock_a": {"laptop": 2, "phone": 1},
        "clock_b": {"laptop": 1, "phone": 3},
    }
    resp = client.post("/sync/vector-clock/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["relation"] == "CONCURRENT"
    assert data["merged_clock"] == {"laptop": 2, "phone": 3}
