"""Vector Clock Engine for Decentralized Causal Ordering.
Tracks partial order of events in distributed multi-device systems.
"""
from __future__ import annotations
from enum import Enum
from typing import Any


class CausalRelation(str, Enum):
    IDENTICAL = "IDENTICAL"
    ANCESTOR = "ANCESTOR"
    DESCENDANT = "DESCENDANT"
    CONCURRENT = "CONCURRENT"


class VectorClock:
    """Represents a vector clock mapping device_id -> logical sequence counter."""

    def __init__(self, clock: dict[str, int] | None = None) -> None:
        self.clock: dict[str, int] = dict(clock) if clock else {}

    def get(self, device_id: str) -> int:
        return self.clock.get(device_id, 0)

    def increment(self, device_id: str) -> None:
        self.clock[device_id] = self.get(device_id) + 1

    def merge(self, other: VectorClock) -> VectorClock:
        """Returns a new VectorClock with component-wise maximums."""
        all_keys = set(self.clock.keys()) | set(other.clock.keys())
        merged = {k: max(self.get(k), other.get(k)) for k in all_keys}
        return VectorClock(merged)

    def compare(self, other: VectorClock) -> CausalRelation:
        """Compares two vector clocks causally.
        - IDENTICAL: all components equal
        - ANCESTOR: self <= other for all components and < for at least one (self happened-before other)
        - DESCENDANT: self >= other for all components and > for at least one (other happened-before self)
        - CONCURRENT: independent concurrent branches
        """
        all_keys = set(self.clock.keys()) | set(other.clock.keys())
        less_than = False
        greater_than = False

        for k in all_keys:
            v1 = self.get(k)
            v2 = other.get(k)
            if v1 < v2:
                less_than = True
            elif v1 > v2:
                greater_than = True

        if not less_than and not greater_than:
            return CausalRelation.IDENTICAL
        if less_than and not greater_than:
            return CausalRelation.ANCESTOR
        if greater_than and not less_than:
            return CausalRelation.DESCENDANT
        return CausalRelation.CONCURRENT

    def to_dict(self) -> dict[str, int]:
        return dict(self.clock)
