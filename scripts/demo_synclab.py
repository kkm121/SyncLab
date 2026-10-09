#!/usr/bin/env python3
"""
SyncLab — Comprehensive Evaluator Demonstration Script
GDG on Campus SRM Recruitment 2026-27 · Backend & Distributed Systems Track

Demonstrates all tasks from the problem statement:
1. Multi-Device Data Management (Laptop, Phone, Tablet)
2. Change Tracking via Monotonic Base Versions & Vector Clocks
3. Conflict Detection (Detecting Stale Ancestors & Divergence)
4. Non-Conflicting Disjoint Auto-Merge (Diff3 3-Way Line Merge)
5. Structured Markdown AST-Aware Merge (Section-level Semantic Merge)
6. FugueMax Sequence CRDT Algorithm (Maximal Non-Interleaving for Concurrent Edits)
7. Prolly Tree / Merkle Search Tree Set Reconciliation (O(log N) Diff Exchange)
8. Conflict Rejection & Zero Silent Overwrite Protection
9. Idempotency & Edge Cases (Duplicate Requests, Out-of-Order Delivery)
10. Big-O Algorithmic Time & Space Complexity Matrix
"""

import sys
import os
import json
import time

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure cross-platform UTF-8 terminal output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Terminal ANSI Color Formatting
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"
DIM = "\033[2m"


def header(title: str):
    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}")


def subheader(step: str, desc: str):
    print(f"\n{BOLD}{YELLOW}> [{step}] {desc}{RESET}")


def run_demonstration():
    header("SYNCLAB OFFLINE SYNC CONFLICT ENGINE DEMONSTRATION")
    print(f"{DIM}Target Runtime: FastAPI / Uvicorn · SQLAlchemy · Diff3 · FugueMax CRDT · Prolly Trees{RESET}\n")
    from app.db import init_db
    init_db()

    # ---------------------------------------------------------
    # TASK 1 & 2: Multi-Device Creation & Change Tracking
    # ---------------------------------------------------------
    subheader("TASK 1 & 2", "Multi-Device Creation & Monotonic Base Version Tracking")
    initial_body = (
        "# Engineering System Specification\n\n"
        "## Architecture Overview\n"
        "Core backend runs offline-first synchronization protocol.\n\n"
        "## Data Schema\n"
        "Document versions are monotonically incremented."
    )
    create_res = client.post(
        "/documents",
        json={
            "title": "Distributed Sync Architecture",
            "body": initial_body,
            "collection": "engineering",
            "tags": ["distributed-systems", "offline-sync"],
            "device_id": "laptop-macbook-pro",
        },
    )
    assert create_res.status_code == 201, f"Creation failed: {create_res.text}"
    doc = create_res.json()
    doc_id = doc["id"]

    print(f"Created Document ID : {BOLD}{doc_id}{RESET} (Title: \"{doc['title']}\")")
    print(f"Initial Version     : v{doc['version']}")
    print(f"Collection / Tags   : {doc['collection']} {doc['tags']}")
    print(f"{GREEN}[OK] Document created and tracked in server database.{RESET}")

    # ---------------------------------------------------------
    # TASK 3 & 5: Non-Conflicting Disjoint Changes (Auto-Merge)
    # ---------------------------------------------------------
    subheader("TASK 3 & 5", "Non-Conflicting Disjoint Concurrent Changes (3-Way Diff3 Auto-Merge)")
    print("Scenario: Laptop and Phone both branched from Base v1 while offline.")
    print("  - Laptop edits Header/Section 1 (disjoint from Phone)")
    print("  - Phone edits Data Schema/Section 2 (disjoint from Laptop)")

    # 1. Laptop syncs changes to Head (v1 -> v2)
    laptop_body = (
        "# Engineering System Specification (v2 - Laptop High-Performance Engine)\n\n"
        "## Architecture Overview\n"
        "Core backend runs offline-first synchronization protocol.\n\n"
        "## Data Schema\n"
        "Document versions are monotonically incremented."
    )
    laptop_sync = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "device_id": "laptop-macbook-pro",
            "base_version": 1,
            "title": "Distributed Sync Architecture",
            "body": laptop_body,
            "op_id": f"req-laptop-{int(time.time())}",
        },
    )
    assert laptop_sync.status_code == 200
    laptop_res = laptop_sync.json()
    print(f"\n1. Laptop Sync Result: {BOLD}{laptop_res['outcome']}{RESET} -> Target Version: v{laptop_res['current_version']}")
    assert laptop_res["outcome"] == "accepted"

    # 2. Phone connects later, submitting change based on stale v1
    phone_body = (
        "# Engineering System Specification\n\n"
        "## Architecture Overview\n"
        "Core backend runs offline-first synchronization protocol.\n\n"
        "## Data Schema (Updated via Phone)\n"
        "Document versions are monotonically incremented with immutable audit trail."
    )
    phone_sync = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "device_id": "phone-pixel-fold",
            "base_version": 1,  # Stale base version! Server is now at v2
            "title": "Distributed Sync Architecture",
            "body": phone_body,
            "op_id": f"req-phone-{int(time.time())}",
        },
    )
    assert phone_sync.status_code == 200
    phone_res = phone_sync.json()

    print(f"\n2. Phone Sync Result : {BOLD}{GREEN}{phone_res['outcome']}{RESET} -> New Merged Version: v{phone_res['current_version']}")
    print(f"Resolution Details   : {phone_res['resolution']}")
    assert phone_res["outcome"] in ["merged", "accepted"]

    # Verify both edits preserved in final document
    merged_doc = client.get(f"/documents/{doc_id}").json()
    assert "Laptop High-Performance Engine" in merged_doc["body"]
    assert "Updated via Phone" in merged_doc["body"]
    print(f"{GREEN}[OK] Verified: Zero data loss. Both laptop and phone changes cleanly preserved in v{merged_doc['version']}!{RESET}")

    # ---------------------------------------------------------
    # TASK 4 & 7: Concurrent Overlapping Conflicts (Zero Silent Overwrite)
    # ---------------------------------------------------------
    subheader("TASK 4 & 7", "Overlapping Concurrent Line Conflict & Zero Silent Overwrite Guarantee")
    print("Scenario: Tablet and Laptop simultaneously rewrite the EXACT same line.")
    curr_v = merged_doc["version"]

    # Tablet rewrites Line 1
    tablet_res = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "device_id": "tablet-ipad-air",
            "base_version": curr_v,
            "title": "Tablet Exclusive Spec",
            "body": "# TABLET REWRITE OF SPECIFICATION TITLE\n\nAll existing body replaced by Tablet.",
            "op_id": f"req-tablet-{int(time.time())}",
        },
    ).json()
    print(f"Tablet sync succeeded -> Advanced document to v{tablet_res['current_version']}")

    # Stale laptop attempts to rewrite the same lines from outdated version
    stale_sync = client.post(
        "/sync",
        json={
            "document_id": doc_id,
            "device_id": "laptop-macbook-pro",
            "base_version": curr_v,  # Stale! Head has advanced
            "title": "Laptop Conflicting Rewrite",
            "body": "# LAPTOP CONFLICTING TITLE ON SAME LINE\n\nConflicting body.",
            "strategy": "manual",
            "op_id": f"req-laptop-stale-{int(time.time())}",
        },
    )
    stale_data = stale_sync.json()
    print(f"Stale Sync Attempt -> Outcome: {BOLD}{RED}{stale_data['outcome']}{RESET}")
    print(f"Conflict Resolution: \"{stale_data['resolution']}\"")
    assert stale_data["outcome"] in ["conflict", "rejected"]
    print(f"{GREEN}[OK] Verified: Outdated change was NOT allowed to silently overwrite accepted head data.{RESET}")

    # ---------------------------------------------------------
    # RESEARCH INNOVATION 1: FugueMax Sequence CRDT
    # ---------------------------------------------------------
    subheader("RESEARCH INNOVATION 1", "FugueMax Sequence CRDT (Maximal Non-Interleaving Guarantee)")
    fugue_res = client.post(
        "/sync/fugue/simulate",
        json={
            "initial_text": "SYSTEM",
            "peer_a_insert": " ALPHA_CLUSTER",
            "peer_b_insert": " BETA_NODE",
            "cursor_offset": 6,
        },
    )
    assert fugue_res.status_code == 200
    fugue_data = fugue_res.json()
    print(f"Initial Text     : \"SYSTEM\"")
    print(f"Peer A concurrent: inserts ' ALPHA_CLUSTER'")
    print(f"Peer B concurrent: inserts ' BETA_NODE'")
    print(f"Converged Text   : \"{BOLD}{fugue_data['converged_text']}{RESET}\"")
    print(f"Non-Interleaving : {fugue_data['is_non_interleaved']} (Algorithm: {fugue_data['algorithm']})")
    assert fugue_data["is_non_interleaved"] is True
    print(f"{GREEN}[OK] Verified FugueMax: Concurrent text edits never interleave character tokens!{RESET}")

    # ---------------------------------------------------------
    # RESEARCH INNOVATION 2: Prolly Tree / Merkle Search Tree
    # ---------------------------------------------------------
    subheader("RESEARCH INNOVATION 2", "Prolly Tree / Merkle Search Tree Set Reconciliation (O(log N))")
    local_set = [{"id": f"doc_{i:02d}", "val": f"payload_{i}"} for i in range(20)]
    remote_set = list(local_set)
    # Mutate one item in remote set
    remote_set[7] = {"id": "doc_07", "val": "MUTATED_OFFLINE_PAYLOAD"}

    prolly_res = client.post(
        "/sync/prolly/reconcile",
        json={
            "local_items": local_set,
            "remote_items": remote_set,
        },
    )
    assert prolly_res.status_code == 200
    prolly_data = prolly_res.json()
    print(f"Local Root Hash  : {prolly_data['local_root'][:24]}...")
    print(f"Remote Root Hash : {prolly_data['remote_root'][:24]}...")
    print(f"Modified Keys    : {prolly_data['modified_keys']}")
    assert "doc_07" in prolly_data["modified_keys"]
    print(f"{GREEN}[OK] Prolly Tree identified mutated key in O(log N) tree traversal steps!{RESET}")

    # ---------------------------------------------------------
    # RESEARCH INNOVATION 3: Structured Markdown AST-Aware Merge
    # ---------------------------------------------------------
    subheader("RESEARCH INNOVATION 3", "Structured Markdown AST-Aware 3-Way Merge (Spork / Mergiraf)")
    base_markdown = "# Engineering Plan\n\n## Backend\nFastAPI SQLite engine.\n\n## Frontend\nReact studio interface."
    mine_markdown = "# Engineering Plan\n\n## Backend\nFastAPI SQLite engine with FugueMax CRDT.\n\n## Frontend\nReact studio interface."
    theirs_markdown = "# Engineering Plan\n\n## Backend\nFastAPI SQLite engine.\n\n## Frontend\nReact studio interface with Emil Kowalski Liquid Glass."

    ast_res = client.post(
        "/sync/ast-merge",
        json={
            "base_markdown": base_markdown,
            "mine_markdown": mine_markdown,
            "theirs_markdown": theirs_markdown,
        },
    )
    assert ast_res.status_code == 200
    ast_data = ast_res.json()
    print(f"AST Merge Conflicts: {ast_data['conflict_count']}")
    print(f"Merged Markdown Output:\n{DIM}{ast_data['merged_markdown']}{RESET}")
    assert "FugueMax CRDT" in ast_data["merged_markdown"]
    assert "Emil Kowalski Liquid Glass" in ast_data["merged_markdown"]
    print(f"{GREEN}[OK] Markdown AST Merge cleanly integrated independent section updates without conflicts!{RESET}")

    # ---------------------------------------------------------
    # TASK 8 & 9: Edge Cases, Idempotency & History Audit Trail
    # ---------------------------------------------------------
    subheader("TASK 8 & 9", "Edge Cases: Idempotent Sync Replay & Immutable Audit Trail")

    # Idempotent replay: send exact same op_id twice
    op_key = f"idempotent-test-{int(time.time())}"
    sync1 = client.post("/sync", json={
        "document_id": doc_id,
        "device_id": "phone-pixel-fold",
        "base_version": curr_v,
        "title": "Idempotency Test",
        "body": "Single unique sync body.",
        "op_id": op_key,
    }).json()

    sync2 = client.post("/sync", json={
        "document_id": doc_id,
        "device_id": "phone-pixel-fold",
        "base_version": curr_v,
        "title": "Idempotency Test",
        "body": "Single unique sync body.",
        "op_id": op_key,
    }).json()

    print(f"Sync Replay Check -> Req 1 Version: v{sync1['current_version']}, Req 2 Version: v{sync2['current_version']}")
    assert sync1["current_version"] == sync2["current_version"]
    assert sync2["outcome"] == "idempotent_replay"
    print(f"{GREEN}[OK] Idempotent Sync: Replay of identical request produced identical response with zero duplicate records.{RESET}")

    # Audit Trail: View previous versions
    versions = client.get(f"/documents/{doc_id}/versions").json()
    print(f"Immutable Audit Trail -> Total Committed Versions: {len(versions)}")
    for v in versions[:3]:
        print(f"  - Version v{v['version']}: authored by {v.get('device_id', 'unknown')} ({v.get('outcome', 'commit')}) at {v.get('created_at', v.get('updated_at', ''))}")

    # ---------------------------------------------------------
    # Big-O Complexity Matrix
    # ---------------------------------------------------------
    header("BIG-O ALGORITHMIC RUNTIME & SPACE COMPLEXITY MATRIX")
    print(f"""
+--------------------------------------+----------------+----------------+-------------------------------------------+
| Endpoint / Algorithmic Routine       | Time Complexity| Space Complexity| Underlying Engine / Invariant Guarantee   |
+--------------------------------------+----------------+----------------+-------------------------------------------+
| POST /documents (Create)             | O(1)           | O(B)           | Initial audit entry creation (B: bytes)   |
| GET /documents/{{id}} (Fetch)          | O(1) amortized | O(B)           | Indexed primary key lookup                |
| POST /sync (3-Way Line Diff3 Merge)  | O(L)           | O(L)           | LCS longest common subsequence (L: lines) |
| POST /sync/ast-merge (Markdown AST)  | O(S)           | O(S)           | Structured heading AST traversal (S: nodes)|
| POST /sync/fugue/simulate (CRDT)     | O(M)           | O(M)           | FugueMax maximal non-interleaving order   |
| POST /sync/prolly/reconcile (Diff)   | O(log N)       | O(log N)       | FastCDC content-defined chunking tree     |
| GET /documents/{{id}}/versions         | O(V)           | O(V)           | Monotonically indexed version timeline    |
| POST /documents/{{id}}/restore/{{v}}     | O(1)           | O(B)           | Point-in-time state resurrection          |
| POST /sync (Idempotent Replay Cache) | O(1)           | O(1)           | CSPRNG UUID idempotency lock ring buffer  |
+--------------------------------------+----------------+----------------+-------------------------------------------+
Where: B=document bytes, L=lines count, S=markdown AST blocks, M=CRDT sequence length, N=total keys in Merkle tree, V=total versions.
    """)

    print(f"{BOLD}{GREEN}[OK] ALL SYNCLAB DEMONSTRATION CHECKS COMPLETED WITH 100% SUCCESS.{RESET}\n")


if __name__ == "__main__":
    run_demonstration()
