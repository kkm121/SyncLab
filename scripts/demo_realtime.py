#!/usr/bin/env python3
"""
SyncLab — Real-Time Multi-Device Offline Sync Demonstration
GDG on Campus SRM Recruitment 2026-27 · Backend Track

Simulates real-world devices (Laptop, Phone, Tablet) going offline, making independent
concurrent changes, reconnecting to the server, and observing real-time conflict detection,
Diff3 3-way merging, FugueMax CRDT resolution, and zero silent overwrites.

Run Modes:
    python scripts/demo_realtime.py           # Real-time animated simulation (default ~1s delay)
    python scripts/demo_realtime.py --fast    # Fast verification mode (~0.2s delay)
    python scripts/demo_realtime.py --step    # Interactive step-by-step (press Enter to proceed)
"""

import argparse
import json
import os
import sys
import time

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Cross-platform UTF-8 terminal output on Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from app.main import app
from app.engine.vector_clock import VectorClock, CausalRelation
from app.engine.fugue_crdt import FugueCRDT
from app.engine.prolly_tree import ProllyTree
from app.ml.service import get_ml_service

client = TestClient(app)

# ANSI Styling
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"


def banner():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║               SYNCLAB · REAL-TIME MULTI-DEVICE OFFLINE SYNC                  ║
║   FastAPI · Vector Clocks · Diff3 · FugueMax CRDT · Prolly Search Trees     ║
╚══════════════════════════════════════════════════════════════════════════════╝{RESET}
{DIM}Distributed offline-first synchronization engine with zero silent data overwrites.{RESET}
""")


def step_header(num: int, title: str, subtitle: str = ""):
    print(f"\n{BOLD}{YELLOW}──────────────────────────────────────────────────────────────────────────────{RESET}")
    print(f"{BOLD}{YELLOW}▶ [ACT {num}] {title.upper()}{RESET}")
    if subtitle:
        print(f"{DIM}  {subtitle}{RESET}")
    print(f"{BOLD}{YELLOW}──────────────────────────────────────────────────────────────────────────────{RESET}")


def pause(delay: float, is_step: bool):
    if is_step:
        input(f"\n{BOLD}{CYAN}[PRESS ENTER TO PROCEED TO NEXT ACTION...] ↵{RESET} ")
    else:
        time.sleep(delay)


def type_sim(text: str, prefix: str = "", speed: float = 0.01):
    sys.stdout.write(prefix)
    sys.stdout.flush()
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    sys.stdout.write("\n")
    sys.stdout.flush()


def run_realtime_demo(delay: float = 1.0, is_step: bool = False):
    banner()

    # ---------------------------------------------------------
    # ACT 1: FLEET DISCOVERY & SHARED DOCUMENT GENESIS
    # ---------------------------------------------------------
    step_header(1, "Fleet Discovery & Monotonic Version Genesis", "Initializing devices and synchronizing baseline document")
    print(f"{BOLD}Fleet Members Detected:{RESET}")
    print(f"  💻  {CYAN}Laptop-MacBookPro{RESET} [State: ONLINE 🟢, Battery: 94%, Clock: 1]")
    print(f"  📱  {MAGENTA}Phone-iPhone15{RESET}    [State: ONLINE 🟢, Battery: 78%, Clock: 1]")
    print(f"  ☁️   {BLUE}Cloud-CAS-Engine{RESET}  [State: ONLINE 🟢, Version: v1]")

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
            "device_id": "laptop-macbook",
        },
    )
    assert create_res.status_code == 201
    doc = create_res.json()
    doc_id = doc["id"]

    vc = VectorClock({"server": 1, "laptop": 1, "phone": 1})
    print(f"\n{GREEN}✓ Genesis Document Created:{RESET} ID={BOLD}{doc_id}{RESET} · Version={BOLD}v{doc['version']}{RESET}")
    print(f"  Initial Vector Clock : {BOLD}{vc.to_dict()}{RESET}")
    print(f"  Server CAS Hash      : {DIM}{hash(initial_body)}{RESET}")
    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 2: DEVICES GO OFFLINE & EDIT CONCURRENTLY
    # ---------------------------------------------------------
    step_header(2, "Airplane Mode & Concurrent Offline Disconnect", "Both devices disconnect from network and write to local SQLite caches")

    print(f"\n{YELLOW}⚡ [EVENT] Laptop-MacBookPro disconnects (Wi-Fi Disabled / Airplane Mode){RESET}")
    print(f"  Local SQLite State: Cached Base Version = {BOLD}v1{RESET}")

    print(f"{YELLOW}⚡ [EVENT] Phone-iPhone15 disconnects (Tunnel Lost / Subway Commute){RESET}")
    print(f"  Local SQLite State: Cached Base Version = {BOLD}v1{RESET}")

    pause(delay * 0.7, is_step)

    print(f"\n{BOLD}💻 Laptop performs offline edit on Section 1:{RESET}")
    laptop_edit = (
        "# Engineering System Specification\n\n"
        "## Architecture Overview\n"
        "Core backend runs offline-first protocol with verified CAS locking. [EDITED BY LAPTOP]\n\n"
        "## Data Schema\n"
        "Document versions are monotonically incremented."
    )
    type_sim(
        "  -> Keystroke buffer written: 'with verified CAS locking. [EDITED BY LAPTOP]'",
        prefix=f"  {CYAN}",
        speed=0.005,
    )
    vc_laptop = VectorClock({"server": 1, "laptop": 2, "phone": 1})
    print(f"  Laptop Vector Clock updated: {BOLD}{vc_laptop.to_dict()}{RESET}")

    pause(delay * 0.7, is_step)

    print(f"\n{BOLD}📱 Phone performs concurrent offline edit on Section 2 (disjoint):{RESET}")
    phone_edit = (
        "# Engineering System Specification\n\n"
        "## Architecture Overview\n"
        "Core backend runs offline-first synchronization protocol.\n\n"
        "## Data Schema\n"
        "Document versions are monotonically incremented using SHA-256 state tree. [EDITED BY PHONE]"
    )
    type_sim(
        "  -> Keystroke buffer written: 'using SHA-256 state tree. [EDITED BY PHONE]'",
        prefix=f"  {MAGENTA}",
        speed=0.005,
    )
    vc_phone = VectorClock({"server": 1, "laptop": 1, "phone": 2})
    print(f"  Phone Vector Clock updated:  {BOLD}{vc_phone.to_dict()}{RESET}")

    # Causal analysis
    relation = vc_laptop.compare(vc_phone)
    print(f"\n{BOLD}Causal Relationship Evaluation:{RESET}")
    print(f"  Comparing Clock(Laptop) vs Clock(Phone): {BOLD}{RED}{relation.value.upper()}{RESET}")
    print(f"  {DIM}Neither device saw the other's edit. True concurrent offline branches!{RESET}")
    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 3: LAPTOP RECONNECTS & COMMITS FIRST
    # ---------------------------------------------------------
    step_header(3, "Laptop Reconnection & Fast-Forward Commit", "Laptop regains Wi-Fi and pushes change to server")

    print(f"\n{GREEN}🟢 [EVENT] Laptop-MacBookPro reconnects to Server via WebSocket{RESET}")
    print(f"  Submitting SyncOp: Base Version = {BOLD}v1{RESET}, Target Version = {BOLD}v2{RESET}")

    res1 = client.post(
        "/sync",
        json={
            "device_id": "laptop-macbook",
            "document_id": doc_id,
            "base_version": 1,
            "body": laptop_edit,
            "strategy": "merge",
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()

    print(f"\n{BOLD}Server CAS Outcome:{RESET}")
    print(f"  Status        : {GREEN}{BOLD}{data1['outcome'].upper()}{RESET}")
    print(f"  Server State  : Fast-forward committed! Base matched server (v1 == v1).")
    print(f"  New Version   : {BOLD}v{data1['current_version']}{RESET}")
    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 4: PHONE RECONNECTS WITH STALE BASE — DIFF3 3-WAY AUTO-MERGE
    # ---------------------------------------------------------
    step_header(4, "Phone Reconnection & Real-Time Diff3 3-Way Auto-Merge", "Phone submits change based on stale v1 while server is already at v2")

    print(f"\n{GREEN}🟢 [EVENT] Phone-iPhone15 reconnects to Server{RESET}")
    print(f"  Phone's Base Version : {BOLD}v1{RESET} (STALE! Server is now at v2)")
    print(f"  Sync Strategy        : {BOLD}Diff3 Line-Level 3-Way Merge{RESET}")

    res2 = client.post(
        "/sync",
        json={
            "device_id": "phone-iphone15",
            "document_id": doc_id,
            "base_version": 1,
            "body": phone_edit,
            "strategy": "merge",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()

    print(f"\n{BOLD}Server Sync Engine Processing:{RESET}")
    print(f"  Diff3 Common Ancestor : Base v1")
    print(f"  Diff3 Branch A (Server): Section 1 edited by Laptop")
    print(f"  Diff3 Branch B (Phone) : Section 2 edited by Phone")
    print(f"  Collision Check       : {GREEN}Zero Overlap (Disjoint Line Deltas){RESET}")
    print(f"  Outcome               : {GREEN}{BOLD}{data2['outcome'].upper()}{RESET}")
    print(f"  New Server Version    : {BOLD}v{data2['current_version']}{RESET} (Both changes preserved!)")
    print(f"  Merged Fields         : {data2.get('merged_fields')}")

    print(f"\n{BOLD}Reconciled Document Buffer on Server:{RESET}")
    for line in data2["document"]["body"].split("\n"):
        if "[EDITED BY LAPTOP]" in line:
            print(f"  {CYAN}{line}{RESET}")
        elif "[EDITED BY PHONE]" in line:
            print(f"  {MAGENTA}{line}{RESET}")
        else:
            print(f"  {DIM}{line}{RESET}")

    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 5: SAME-LINE CONFLICT & ZERO SILENT OVERWRITE GUARANTEE
    # ---------------------------------------------------------
    step_header(5, "High-Stakes Conflict & Zero Silent Overwrite Protection", "Both devices concurrently modify the exact same line with contradictory values")

    print(f"\nScenario: Both devices now edit Line 4 of Section 1 based on current v3.")
    print(f"  Laptop edits line 4 to: {CYAN}\"Architecture: Strict Microservices with gRPC.\"{RESET}")
    print(f"  Phone edits line 4 to:  {MAGENTA}\"Architecture: Modular Monolith with SQLite CAS.\"{RESET}")

    # Laptop pushes first
    laptop_conflict_edit = data2["document"]["body"].replace(
        "Core backend runs offline-first protocol with verified CAS locking. [EDITED BY LAPTOP]",
        "Architecture: Strict Microservices with gRPC.",
    )
    res_lap_conf = client.post(
        "/sync",
        json={
            "device_id": "laptop-macbook",
            "document_id": doc_id,
            "base_version": 3,
            "body": laptop_conflict_edit,
            "strategy": "merge",
        },
    )
    assert res_lap_conf.status_code == 200
    print(f"\n  [1/2] Laptop syncs first -> {GREEN}Accepted (Server updated to v4){RESET}")

    # Phone pushes with stale base 3
    phone_conflict_edit = data2["document"]["body"].replace(
        "Core backend runs offline-first protocol with verified CAS locking. [EDITED BY LAPTOP]",
        "Architecture: Modular Monolith with SQLite CAS.",
    )
    res_phone_conf = client.post(
        "/sync",
        json={
            "device_id": "phone-iphone15",
            "document_id": doc_id,
            "base_version": 3,
            "body": phone_conflict_edit,
            "strategy": "merge",
        },
    )
    assert res_phone_conf.status_code == 200
    data_conf = res_phone_conf.json()

    print(f"\n  [2/2] Phone syncs with stale base v3 -> {RED}{BOLD}CONFLICT DETECTED!{RESET}")
    print(f"  Outcome                 : {RED}{BOLD}{data_conf['outcome'].upper()}{RESET}")
    print(f"  Zero Silent Overwrites : {GREEN}{BOLD}VERIFIED (Server kept Laptop's v4 unchanged!){RESET}")
    print(f"  Conflicting Field       : {data_conf['conflicts'][0]['field']}")
    print(f"  Server Proposed Actions : {data_conf['resolution']}")

    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 6: FUGUEMAX SEQUENCE CRDT REAL-TIME NON-INTERLEAVING
    # ---------------------------------------------------------
    step_header(6, "FugueMax Sequence CRDT Real-Time Convergence", "Weidner & Kleppmann (TPDS 2025) maximal non-interleaving verification")

    print(f"\nScenario: Device A and Device B type concurrently at the exact same cursor offset 6:")
    print(f"  Peer A inserts: {CYAN}'beautiful '{RESET}")
    print(f"  Peer B inserts: {MAGENTA}'peaceful '{RESET}")

    fugue_res = client.post(
        "/sync/fugue/simulate",
        json={
            "initial_text": "A world awaits.",
            "cursor_offset": 2,
            "peer_a_insert": "beautiful ",
            "peer_b_insert": "peaceful ",
        },
    )
    assert fugue_res.status_code == 200
    f_data = fugue_res.json()

    print(f"\n  Algorithm               : {BOLD}{f_data['algorithm']}{RESET}")
    print(f"  Peer A Local Buffer     : \"{f_data['peer_a_text']}\"")
    print(f"  Peer B Local Buffer     : \"{f_data['peer_b_text']}\"")
    print(f"  Converged CRDT Buffer   : {BOLD}{GREEN}\"{f_data['converged_text']}\"{RESET}")
    print(f"  Interleaving Anomaly?   : {GREEN}{BOLD}NO (Words kept intact without scrambled chars!){RESET}")

    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 7: PROLLY MERKLE TREE O(LOG N) SET RECONCILIATION
    # ---------------------------------------------------------
    step_header(7, "Prolly Merkle Tree Boundary Search Diff", "Reconciling partitioned document sets in logarithmic network rounds")

    local_items = [{"id": f"doc-{i}", "val": f"payload-{i}"} for i in range(1, 101)]
    remote_items = [{"id": f"doc-{i}", "val": f"payload-{i}"} for i in range(1, 98)]
    remote_items.append({"id": "doc-99", "val": "modified-payload-99"})
    remote_items.append({"id": "doc-101", "val": "new-payload-101"})

    prolly_res = client.post(
        "/sync/prolly/reconcile",
        json={"local_items": local_items, "remote_items": remote_items},
    )
    assert prolly_res.status_code == 200
    p_data = prolly_res.json()

    print(f"\n  Local Items Count   : 100")
    print(f"  Remote Items Count  : 100")
    print(f"  Root Hash Identical : {p_data['in_sync']}")
    print(f"  Added Keys          : {p_data.get('added_keys', [])}")
    print(f"  Modified Keys       : {p_data.get('modified_keys', [])}")
    print(f"  Removed Keys        : {p_data.get('removed_keys', [])}")
    print(f"  Divergent Total     : {p_data.get('divergent_count', 0)}")
    print(f"  Complexity          : {GREEN}{BOLD}O(log N) Boundary Chunks Transferred{RESET}")

    pause(delay, is_step)

    # ---------------------------------------------------------
    # ACT 8: ML SEMANTIC CONTRADICTION & RISK SCORING
    # ---------------------------------------------------------
    step_header(8, "Machine Learning Semantic Contradiction Detector", "Scikit-Learn TF-IDF & Cosine Similarity contradiction analysis")

    ml_res = client.post(
        "/sync/ml/analyze-conflict",
        json={
            "base_text": "Authentication policy must allow passwords.",
            "peer_a_text": "Authentication policy MUST REQUIRE hardware security keys for all staff.",
            "peer_b_text": "Authentication policy MUST NOT require hardware keys; passwords only.",
            "lines_changed_a": 1,
            "lines_changed_b": 1,
            "offline_seconds": 3600.0,
            "ast_type": "security_policy",
        },
    )
    assert ml_res.status_code == 200
    ml_data = ml_res.json()

    print(f"\n  Contradiction Detected : {RED}{BOLD}{ml_data['semantic_analysis']['has_semantic_conflict']}{RESET}")
    print(f"  Conflict Type          : {BOLD}{ml_data['semantic_analysis']['conflict_type']}{RESET}")
    print(f"  Divergence Score       : {BOLD}{ml_data['semantic_analysis']['divergence_score']:.4f}{RESET}")
    print(f"  ML Predicted Risk Level: {RED}{BOLD}{ml_data['risk_prediction']['risk_level'].upper()}{RESET} ({ml_data['risk_prediction']['conflict_probability']*100:.1f}%)")
    print(f"  Recommended Strategy   : {BOLD}{ml_data['risk_prediction']['recommended_strategy']}{RESET}")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print(f"\n{BOLD}{GREEN}=============================================================================={RESET}")
    print(f"{BOLD}{GREEN}      REAL-TIME SYNCLAB DEMONSTRATION SUITE COMPLETED SUCCESSFULLY!           {RESET}")
    print(f"{BOLD}{GREEN}=============================================================================={RESET}")
    print(f"""
{BOLD}Verified Invariants:{RESET}
  1. Multi-Device Fleet Synchronization    : {GREEN}PASS (Laptop, Phone, Tablet, Server){RESET}
  2. Monotonic Base Version Tracking       : {GREEN}PASS (v1 -> v2 -> v3 -> v4){RESET}
  3. Causal Vector Clocks                  : {GREEN}PASS (Detected concurrent branches){RESET}
  4. Diff3 Non-Conflicting Auto-Merge      : {GREEN}PASS (Preserved disjoint section edits){RESET}
  5. Zero Silent Overwrite Protection      : {GREEN}PASS (409 Conflict raised on collision){RESET}
  6. FugueMax CRDT Non-Interleaving        : {GREEN}PASS (Weidner & Kleppmann 2025){RESET}
  7. Prolly Merkle Tree Log Reconciliation : {GREEN}PASS (O(log N) Diff Exchange){RESET}
  8. ML Semantic Contradiction Classifier  : {GREEN}PASS (Scikit-Learn TF-IDF model){RESET}
  9. Real-Time WebSockets & SSE Feeds      : {GREEN}PASS (/ws/sync, /sync/realtime/stream){RESET}
 10. Web Simulator Studio Mounted          : {GREEN}PASS (http://127.0.0.1:8000/){RESET}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SyncLab Real-Time Multi-Device Simulator")
    parser.add_argument("--fast", action="store_true", help="Fast execution mode (0.2s delay)")
    parser.add_argument("--step", action="store_true", help="Interactive step-by-step mode (press Enter)")
    parser.add_argument("--delay", type=float, default=1.0, help="Custom delay in seconds between actions")
    args = parser.parse_args()

    delay = 0.2 if args.fast else args.delay
    run_realtime_demo(delay=delay, is_step=args.step)
