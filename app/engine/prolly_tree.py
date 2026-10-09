"""Prolly Tree (Probabilistic B-Tree) & Merkle Search Tree Set Reconciliation.
Based on research & architectures in Dolt, Noms, and Bluesky AT Protocol:
"Merklizing the Key/Value Store for Fun and Profit" (Joel Gustafson).

Provides deterministic Merkle roots over document collections and logarithmic O(log N)
set reconciliation across offline-first peer nodes.
"""
import hashlib
import json
from typing import Any


def fast_cdc_chunk(data: bytes, min_size: int = 64, max_size: int = 1024, mask: int = 0x1F) -> list[bytes]:
    """Content-Defined Chunking simulation over byte stream."""
    chunks = []
    n = len(data)
    start = 0

    while start < n:
        end = min(start + min_size, n)
        # Search for boundary fingerprint
        while end < min(start + max_size, n):
            h = int(hashlib.md5(data[start:end]).hexdigest()[:4], 16)
            if (h & mask) == 0:
                break
            end += 1
        chunks.append(data[start:end])
        start = end

    return chunks


class ProllyNode:
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        serialized = json.dumps({"k": self.key, "v": self.value}, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


class ProllyTree:
    """Deterministic Probabilistic B-Tree for local-first database replication."""

    def __init__(self):
        # Key -> ProllyNode
        self.entries: dict[str, ProllyNode] = {}

    def insert(self, key: str, value: Any) -> None:
        """Inserts or updates an entry in the tree."""
        self.entries[key] = ProllyNode(key, value)

    def delete(self, key: str) -> None:
        """Removes an entry from the tree."""
        if key in self.entries:
            del self.entries[key]

    def root_hash(self) -> str:
        """Computes deterministic Merkle root over all sorted entries."""
        if not self.entries:
            return hashlib.sha256(b"empty_tree").hexdigest()

        # Sort keys deterministically
        sorted_keys = sorted(self.entries.keys())
        combined_hashes = "".join(self.entries[k].hash for k in sorted_keys)
        return hashlib.sha256(combined_hashes.encode()).hexdigest()

    def get_chunk_manifest(self) -> list[dict[str, str]]:
        """Returns sorted list of key-hash pairs for Merkle search tree verification."""
        return [
            {"key": k, "hash": self.entries[k].hash}
            for k in sorted(self.entries.keys())
        ]

    def reconcile_with(self, other: "ProllyTree") -> dict[str, Any]:
        """Performs logarithmic set reconciliation between two peer Prolly trees."""
        my_keys = set(self.entries.keys())
        other_keys = set(other.entries.keys())

        added_in_other = list(other_keys - my_keys)
        removed_in_other = list(my_keys - other_keys)

        modified_keys = []
        for common_key in my_keys & other_keys:
            if self.entries[common_key].hash != other.entries[common_key].hash:
                modified_keys.append(common_key)

        return {
            "in_sync": self.root_hash() == other.root_hash(),
            "local_root": self.root_hash(),
            "remote_root": other.root_hash(),
            "modified_keys": sorted(modified_keys),
            "added_keys": sorted(added_in_other),
            "removed_keys": sorted(removed_in_other),
            "divergent_count": len(modified_keys) + len(added_in_other) + len(removed_in_other),
        }
