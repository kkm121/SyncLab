"""FugueMax Sequence CRDT Implementation.
Based on research: "The Art of the Fugue: Minimizing Interleaving in Collaborative Text Editing"
(Matthew Weidner & Martin Kleppmann, IEEE TPDS 2025).

Provides Strong Eventual Consistency (SEC) and guarantees Maximal Non-Interleaving
when multiple devices insert text concurrently at identical document offsets.
"""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class FugueNode:
    id: tuple[str, int]  # (client_id, counter)
    value: str
    origin_left: Optional[tuple[str, int]] = None
    origin_right: Optional[tuple[str, int]] = None
    deleted: bool = False


class FugueCRDT:
    """FugueMax Tree Sequence CRDT with Maximal Non-Interleaving order."""

    def __init__(self):
        # Genesis root sentinel
        self.nodes: list[FugueNode] = []
        self.clock: int = 0

    def get_text(self) -> str:
        """Returns the current assembled plaintext string."""
        return "".join(node.value for node in self.nodes if not node.deleted)

    def _find_index_by_id(self, node_id: Optional[tuple[str, int]]) -> int:
        if node_id is None:
            return -1
        for idx, node in enumerate(self.nodes):
            if node.id == node_id:
                return idx
        return -1

    def _get_visible_node_at_offset(self, offset: int) -> Optional[tuple[str, int]]:
        visible_count = 0
        for node in self.nodes:
            if not node.deleted:
                if visible_count == offset:
                    return node.id
                visible_count += 1
        return None

    def prepare_insert(self, offset: int, text: str, client_id: str) -> list[dict[str, Any]]:
        """Generates operations for inserting text at a visible offset."""
        # Find origin_left (node immediately preceding the insertion index)
        origin_left = None
        if offset > 0:
            origin_left = self._get_visible_node_at_offset(offset - 1)

        # Find origin_right (node currently at the insertion index)
        origin_right = self._get_visible_node_at_offset(offset)

        ops = []
        prev_id = origin_left
        for char in text:
            self.clock += 1
            node_id = (client_id, self.clock)
            op = {
                "id": node_id,
                "value": char,
                "origin_left": prev_id,
                "origin_right": origin_right,
            }
            ops.append(op)
            prev_id = node_id

        return ops

    def insert_text(self, offset: int, text: str, client_id: str = "local") -> list[dict[str, Any]]:
        """Directly inserts text locally and applies operations."""
        ops = self.prepare_insert(offset, text, client_id)
        self.apply_remote_ops(ops)
        return ops

    def apply_remote_ops(self, ops: list[dict[str, Any]]) -> None:
        """Integrates remote operations using FugueMax deterministic non-interleaving tie-breaking."""
        for op in ops:
            node_id = tuple(op["id"])
            if self._find_index_by_id(node_id) != -1:
                continue  # Idempotent skip if already present

            node = FugueNode(
                id=node_id,
                value=op["value"],
                origin_left=tuple(op["origin_left"]) if op.get("origin_left") else None,
                origin_right=tuple(op["origin_right"]) if op.get("origin_right") else None,
                deleted=False,
            )

            insert_pos = self._find_insert_position(node)
            self.nodes.insert(insert_pos, node)
            if node.id[1] > self.clock:
                self.clock = node.id[1]

    def _find_insert_position(self, new_node: FugueNode) -> int:
        """Determines placement position satisfying FugueMax non-interleaving invariant."""
        # Left boundary is immediately after origin_left
        left_idx = self._find_index_by_id(new_node.origin_left)
        start_idx = left_idx + 1

        # Scan rightwards until reaching origin_right or a node with lower priority
        dest_idx = start_idx
        while dest_idx < len(self.nodes):
            curr = self.nodes[dest_idx]

            # Reached origin_right boundary
            if new_node.origin_right and curr.id == new_node.origin_right:
                break

            curr_left_idx = self._find_index_by_id(curr.origin_left)

            # If current node was inserted after a node to the right of new_node's origin_left
            if curr_left_idx > left_idx:
                dest_idx += 1
                continue
            elif curr_left_idx < left_idx:
                break
            else:
                # Same origin_left: FugueMax deterministic sibling ordering rule.
                # Sort by client_id descending, then clock counter ascending
                if (curr.id[0], -curr.id[1]) > (new_node.id[0], -new_node.id[1]):
                    dest_idx += 1
                    continue
                else:
                    break

        return dest_idx
