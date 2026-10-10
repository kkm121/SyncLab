# SyncLab — Distributed Offline-First Sync Engine With ML Intelligence

<p align="left">
  <img src="https://img.shields.io/badge/FastAPI-0.142-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/WebSockets-Live%20Fleet-E0234E.svg" alt="WebSockets">
  <img src="https://img.shields.io/badge/SQLite-file--backed-003B57.svg" alt="SQLite">
  <img src="https://img.shields.io/badge/Tests-42%20passed-16A34A.svg" alt="Tests 42 passed">
  <img src="https://img.shields.io/badge/License-MIT-1D4ED8.svg" alt="License MIT">
</p>

**SyncLab** is an enterprise-grade backend synchronization engine designed to resolve multi-device offline state conflicts without silent data overwrites. Built for **GDG on Campus SRM Technical Domain Recruitment (Backend & Distributed Systems Track)**, SyncLab integrates classic 3-way Diff3 merges, monotonic version tracking, and atomic Compare-And-Swap (CAS) transactions with cutting-edge innovations: **Actual Multi-Device Client CLIs**, **Real-Time WebSocket & SSE Broadcast Channels**, **ML Semantic Conflict Detection**, **FugueMax Sequence CRDTs**, **Prolly Tree Merkle Reconciliation**, and **Distributed Vector Clocks**.

---

## ⚡ How to Run & Demonstrate in Real-Time (Step-by-Step Guide)

SyncLab includes **actual working multi-device client applications** (`scripts/client.py` and the live multi-tab Web Studio) that store persistent local caches and offline mutation outboxes on disk.

### Step 1: Start the SyncLab Backend Server
Open a terminal in the project root and start the server:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Web Studio UI:** [`http://127.0.0.1:8000`](http://127.0.0.1:8000)
- **Swagger OpenAPI Docs:** [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **Health Check:** `http://127.0.0.1:8000/health`

---

### Step 2: Run Actual Multi-Device Clients (Interactive Two-Terminal Mode)

Open **two separate terminal windows** alongside the running server:

```bash
# Terminal Window 1 (Device A: Laptop)
python scripts/client.py --device laptop

# Terminal Window 2 (Device B: Phone)
python scripts/client.py --device phone
```

#### Interactive Workflow to Execute:
1. **Create Document (in Laptop Terminal):**
   ```text
   laptop [ONLINE] > create "Distributed Consensus Engine" "SECTION 1: Core Architecture\nSECTION 2: Storage CAS Engine"
   ```
2. **Pull & Inspect (in Phone Terminal):**
   ```text
   phone [ONLINE] > show 218
   ```
3. **Disconnect Laptop & Edit Offline (in Laptop Terminal):**
   ```text
   laptop [ONLINE] > offline
   laptop [OFFLINE] > edit 218 "SECTION 1: Core Architecture [UPDATED BY LAPTOP OFFLINE]\nSECTION 2: Storage CAS Engine"
   laptop [OFFLINE] > status
   ```
4. **Concurrent Edit on Phone While Online (in Phone Terminal):**
   ```text
   phone [ONLINE] > append 218 "SECTION 3: Real-Time WebSocket Channel [ADDED BY PHONE]"
   ```
5. **Reconnect Laptop & Trigger 3-Way Diff3 Auto-Merge (in Laptop Terminal):**
   ```text
   laptop [OFFLINE] > online
   laptop [ONLINE] > sync 218 merge
   ```
6. **Trigger Same-Line Conflict & Zero Overwrite Protection:**
   - In Laptop Terminal: `offline` $\to$ `edit 218 "SECTION 1: Core Architecture\nSECTION 2: Strictly In-Memory Redis Core\nSECTION 3: WebSocket"`
   - In Phone Terminal: `edit 218 "SECTION 1: Core Architecture\nSECTION 2: Distributed RocksDB SST Core\nSECTION 3: WebSocket"`
   - In Laptop Terminal: `online` $\to$ `sync 218 merge` (Server detects conflict and prevents overwrite!)
   - Resolve conflict: `sync 218 client_wins` (or select option `1–4` in interactive prompt)
7. **Inspect Full Immutable Version History:**
   ```text
   laptop [ONLINE] > history 218
   ```

---

### Step 3: Verified Real-World Execution Transcript

Below is the **actual live terminal transcript** recorded from running the commands above against the live SyncLab backend on `http://127.0.0.1:8000`:

#### 1. Laptop Creates Genesis Document (`v1`) & Phone Pulls Copy
```text
$ python scripts/client.py --device laptop --command "create 'Distributed Consensus Engine' 'SECTION 1: Core Architecture\nSECTION 2: Storage CAS Engine'"
✓ Created Document #218 ('Distributed Consensus Engine') v1 on server!

$ python scripts/client.py --device phone --command "show 218"
=== DOCUMENT #218: Distributed Consensus Engine (v1) ===
Collection : notes
Tags       : ['synclab', 'laptop']
Updated At : 2026-10-10T03:42:59.804248
--- BODY CONTENT ---
SECTION 1: Core Architecture
SECTION 2: Storage CAS Engine
--------------------
```

#### 2. Laptop Enters Airplane Mode (`OFFLINE`) & Stages Local Edit on Section 1
```text
$ python scripts/client.py --device laptop --command "offline"
⚡ Device [laptop] is now OFFLINE (Airplane Mode / Disconnected).
  All edits will be queued in local outbox: .synclab_client\laptop\outbox.json

$ python scripts/client.py --device laptop --command "edit 218 'SECTION 1: Core Architecture [UPDATED BY LAPTOP OFFLINE]\nSECTION 2: Storage CAS Engine'"
⚡ [SAVED OFFLINE] Edit staged in local outbox for Doc #218 (Base v1).
  When ready to synchronize with server, run 'online' and 'sync 218'.

$ python scripts/client.py --device laptop --command "status"
=== DEVICE STATUS: laptop ===
Network Status : OFFLINE ⚡
Server Target  : http://127.0.0.1:8000
Cached Docs    : 2 documents
Pending Outbox : 1 uncommitted offline mutations
Vector Clock   : {'laptop': 4}
```

#### 3. Phone Appends Disjoint Section 3 While Online (Advances Server to `v2`)
```text
$ python scripts/client.py --device phone --command "append 218 'SECTION 3: Real-Time WebSocket Channel [ADDED BY PHONE]'"
--> Synchronizing Doc #218 with Server (Base v1, Strategy: merge)...
✓ [ACCEPTED] Server fast-forward committed revision -> v2
```

#### 4. Laptop Reconnects (`ONLINE`) & Flushes Stale Base `v1` — Diff3 3-Way Auto-Merge (`v3`)
```text
$ python scripts/client.py --device laptop --command "online"
🟢 Device [laptop] is now ONLINE.
  You have 1 pending offline edits in your outbox.
  Run 'sync' to synchronize them with the server.

$ python scripts/client.py --device laptop --command "sync 218 merge"
--> Synchronizing Doc #218 with Server (Base v1, Strategy: merge)...
✓ [DIFF3 AUTO-MERGED] Disjoint concurrent edits merged -> v3
  Merged Fields : ['body']

Merged Result from Server:
SECTION 1: Core Architecture [UPDATED BY LAPTOP OFFLINE]
SECTION 2: Storage CAS Engine
SECTION 3: Real-Time WebSocket Channel [ADDED BY PHONE]
```

#### 5. Overlapping Same-Line Conflict & Zero Silent Overwrite Guarantee (`v4` $\to$ Conflict $\to$ `v5`)
Both devices concurrently rewrite `SECTION 2` with contradictory values based on `v3`:
```text
# Laptop edits Section 2 while OFFLINE (Base v3):
$ python scripts/client.py --device laptop --command "offline"
$ python scripts/client.py --device laptop --command "edit 218 'SECTION 1: Core Architecture [UPDATED BY LAPTOP OFFLINE]\nSECTION 2: Strictly In-Memory Redis Core\nSECTION 3: Real-Time WebSocket Channel [ADDED BY PHONE]'"
⚡ [SAVED OFFLINE] Edit staged in local outbox for Doc #218 (Base v3).

# Phone edits Section 2 while ONLINE (advances Server to v4):
$ python scripts/client.py --device phone --command "edit 218 'SECTION 1: Core Architecture [UPDATED BY LAPTOP OFFLINE]\nSECTION 2: Distributed RocksDB SST Core\nSECTION 3: Real-Time WebSocket Channel [ADDED BY PHONE]'"
--> Synchronizing Doc #218 with Server (Base v3, Strategy: merge)...
✓ [ACCEPTED] Server fast-forward committed revision -> v4

# Laptop reconnects and attempts to sync stale Base v3:
$ python scripts/client.py --device laptop --command "online"
$ python scripts/client.py --device laptop --command "sync 218 merge"
--> Synchronizing Doc #218 with Server (Base v3, Strategy: merge)...
⚠ [CONFLICT DETECTED — ZERO OVERWRITE GUARANTEE]
  The server has advanced to version v4 while your edits were based on v3.
  Server refused to silently overwrite existing data!
  Conflict Details : Same-field edits on both sides; resolve and resubmit.
  Conflicting Fields: ['body']

CHOOSE CONFLICT RESOLUTION STRATEGY:
  [1] Diff3 3-Way Line Merge (Generate Conflict Markers: <<<<<<< / ======= / >>>>>>>)
  [2] Server Wins (Discard local offline change, accept server v4)
  [3] Client Wins (Force your offline change over server)
  [4] FugueMax CRDT (Maximal Non-Interleaving Character Merge)
  [5] Cancel / Keep in local outbox for later

# Laptop explicitly resolves conflict using client_wins -> v5:
$ python scripts/client.py --device laptop --command "sync 218 client_wins"
--> Synchronizing Doc #218 with Server (Base v3, Strategy: client_wins)...
✓ [RESOLVED] Server successfully applied client_wins: Device state forced over v3; overridden: ['body'].
```

#### 6. Verified Immutable Audit History (`v1` through `v5`)
```text
$ python scripts/client.py --device laptop --command "history 218"
=== AUDIT HISTORY FOR DOC #218 (5 versions) ===
  v1   | By: laptop               | Strategy: direct     | Outcome: accepted   | 2026-10-10T03:42:59.816212
  v2   | By: phone                | Strategy: direct     | Outcome: accepted   | 2026-10-10T03:43:27.669222
  v3   | By: laptop               | Strategy: merge      | Outcome: merged     | 2026-10-10T03:43:45.744016
  v4   | By: phone                | Strategy: direct     | Outcome: accepted   | 2026-10-10T03:44:05.415022
  v5   | By: laptop               | Strategy: client_wins | Outcome: resolved   | 2026-10-10T06:51:33.109003
```

---

### Step 4: Live Multi-Tab Web Browser Demonstration

You can also demonstrate real-time multi-device sync visually in your browser:
1. Open [`http://127.0.0.1:8000`](http://127.0.0.1:8000) in **Browser Tab 1** and select `💻 Laptop-MacBook` in the top device bar.
2. Open [`http://127.0.0.1:8000`](http://127.0.0.1:8000) in **Browser Tab 2** and select `📱 Phone-iPhone15`.
3. Click **`[ONLINE 🟢]`** in Tab 1 to switch it to **`[OFFLINE ⚡]`**. Edit the document and click **Save Offline Draft (Local Cache)**.
4. In Tab 2 (while online), edit the document and click **Save & Sync Revision**.
5. In Tab 1, toggle back to **`[ONLINE 🟢]`** and click **Sync Staged Offline Revision**.
6. Observe the live **Diff3 3-Way Merge** or the **Interactive Conflict Resolution Banner** (`Accept Server`, `Force Client Wins`, or `Insert 3-Way Conflict Markers`)!

---

## Key Highlights

- **Zero Silent Overwrites:** Stale writes with `base_version < current_version` are either merged field-by-field or acknowledged as explicit conflicts.
- **Real-Time WebSocket & SSE Broadcast:** Asynchronous `RealtimeHub` pushes `SYNC_ACCEPTED`, `SYNC_MERGED`, and `CONFLICT_DETECTED` events to connected devices.
- **3-Way Line Diff3 Merge:** Disjoint concurrent line modifications from offline devices merge automatically without data loss.
- **ML Semantic Contradiction Engine:** Identifies logical contradictions between non-overlapping edits and predicts merge failure probability.
- **FugueMax Sequence CRDT:** Implements maximal non-interleaving character total-ordering for real-time concurrent typing (Weidner & Kleppmann 2025).
- **Prolly Tree (Content-Defined Chunking):** Probabilistic B-Trees offering $O(\log N)$ Merkle diff set reconciliation.
- **Vector Clock Causal Ordering:** Full causal DAG relationship comparison (`IDENTICAL`, `ANCESTOR`, `DESCENDANT`, `CONCURRENT`).
- **Atomic Compare-And-Swap (CAS):** Race-condition proof database commits on version column.
- **Idempotency Lock:** Unique `op_id` ring-buffer ensures network duplicates return cached responses without re-executing writes.

---

## Table of Contents

- [1. Architecture & Repository Structure](#1-architecture--repository-structure)
- [2. Quickstart & Setup](#2-quickstart--setup)
- [3. Algorithmic Complexity Matrix](#3-algorithmic-complexity-matrix)
- [4. API Endpoints](#4-api-endpoints)
- [5. How Synchronization Works](#5-how-synchronization-works)
- [6. Machine Learning Domain Suite](#6-machine-learning-domain-suite)
- [7. Automated Testing & Verification](#7-automated-testing--verification)
- [8. Community Standards](#8-community-standards)

---

## 1. Architecture & Repository Structure

```
backend-offline-sync/
├── app/
│   ├── engine/
│   │   ├── fugue_crdt.py            # FugueMax CRDT with non-interleaving total order
│   │   ├── prolly_tree.py           # FastCDC Probabilistic Merkle B-Trees
│   │   ├── realtime_hub.py          # WebSocket & SSE real-time broadcast engine
│   │   ├── structured_ast_merge.py  # Markdown heading AST semantic merge
│   │   └── vector_clock.py          # Distributed Vector Clock causal DAG engine
│   ├── ml/
│   │   ├── __init__.py
│   │   └── service.py               # Semantic conflict detector & risk predictor
│   ├── routers/
│   │   ├── devices.py               # Device registry, list & catch-up delta feeds
│   │   ├── documents.py             # Document CRUD, version history, export.md
│   │   ├── realtime.py              # WebSockets, SSE streams & live simulation
│   │   └── sync.py                  # Core sync, batch, CRDT, Prolly & ML routes
│   ├── config.py                    # Environment settings
│   ├── db.py                        # SQLAlchemy session management
│   ├── main.py                      # FastAPI application with CORS & static UI mount
│   ├── models.py                    # SQLAlchemy ORM models
│   ├── obsidian.py                  # Obsidian YAML frontmatter markdown exporter
│   ├── schemas.py                   # Pydantic v2 validation contracts
│   ├── sync_engine.py               # 3-Way Diff3 line merge & scalar resolution
│   └── sync_service.py              # Atomic CAS writes, replay cache, versioning
├── frontend/                        # React TypeScript Studio with Conflict Simulator
├── static/                          # Production-built web assets served by FastAPI
├── scripts/
│   ├── client.py                    # Actual Working Multi-Device Client CLI
│   ├── demo_realtime.py             # Live Real-Time Multi-Device Terminal Walkthrough
│   └── demo_synclab.py              # Evaluator Invariant Verification Script
├── tests/                           # 42 Pytest unit & integration tests
│   ├── test_actual_client.py        # Actual client offline/online/merge integration tests
│   ├── test_realtime.py             # WebSocket, SSE, and live broadcast tests
│   └── ...
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── SECURITY.md
└── requirements.txt
```

---

## 2. Quickstart & Setup

### Prerequisites
- Python 3.11+ (Python 3.14 fully verified)
- Node.js 18+ (only if rebuilding frontend from source; compiled assets are pre-bundled in `static/`)

### Installation
```bash
# Clone the repository
git clone https://github.com/kkm121/SyncLab.git
cd SyncLab

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Live Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 3. Algorithmic Complexity Matrix

| Routine / Endpoint | Time Complexity | Space Complexity | Underlying Invariant Guarantee |
| :--- | :--- | :--- | :--- |
| **POST /documents** (Create) | $O(1)$ | $O(B)$ | Monotonic version 1 audit creation |
| **GET /documents/{id}** (Read) | $O(1)$ amortized | $O(B)$ | Primary key index lookup |
| **POST /sync** (3-Way Diff3) | $O(L)$ | $O(L)$ | Longest Common Subsequence line diff |
| **POST /sync/ast-merge** (Markdown AST) | $O(S)$ | $O(S)$ | Structured AST block traversal |
| **POST /sync/fugue/simulate** (CRDT) | $O(M)$ | $O(M)$ | FugueMax non-interleaving order |
| **POST /sync/prolly/reconcile** (Tree Diff) | $O(\log N)$ | $O(\log N)$ | FastCDC content-defined chunking tree |
| **POST /sync/vector-clock/compare** | $O(D)$ | $O(D)$ | Component-wise causal DAG scan |
| **POST /documents/{id}/restore/{v}** | $O(1)$ | $O(B)$ | Point-in-time state resurrection |
| **WS /ws/sync** (Broadcast) | $O(C)$ | $O(1)$ | Fan-out to $C$ connected subscribers |

*Where $B$: document bytes, $L$: line count, $S$: AST sections, $M$: CRDT sequence length, $N$: Merkle entries, $D$: cluster devices, $C$: active WebSocket connections.*

---

## 4. API Endpoints

### Real-Time Channels
- `WS /ws/sync`: Bidirectional WebSocket endpoint for live fleet synchronization.
- `GET /sync/realtime/stream`: Server-Sent Events (SSE) live event stream.
- `GET /sync/realtime/history`: Fetch recent real-time broadcast event timeline.
- `POST /sync/realtime/simulate`: Run multi-stage real-time simulation scenario.

### Devices & Fleet
- `POST /devices/register`: Register device identity and update presence.
- `GET /devices`: List all registered devices and registration timestamps.
- `GET /devices/{id}/changes`: Catch-up delta feed of mutations since a version.

### Documents & History
- `POST /documents`: Create a new document (starts at version 1).
- `GET /documents/{id}`: Retrieve current state and active version.
- `GET /documents/{id}/versions`: Retrieve immutable point-in-time audit trail.
- `POST /documents/{id}/restore/{v}`: Point-in-time restoration without rewriting history.
- `GET /documents/{id}/export.md`: Export document as Obsidian-compatible Markdown with YAML frontmatter.

### Synchronization
- `POST /sync`: Execute a sync operation (`merge`, `diff3`, `client_wins`, `server_wins`, `manual`).
- `POST /sync/batch`: Atomic multi-operation sync queue flush for reconnecting devices.
- `POST /sync/batch-summary`: Summary statistics for batch operations.

### Cutting-Edge Systems & Machine Learning
- `POST /sync/vector-clock/compare`: Determine causality between distributed nodes.
- `POST /sync/fugue/simulate`: Simulate concurrent text editing with FugueMax CRDT.
- `POST /sync/prolly/reconcile`: Exchange content-defined Merkle trees in $O(\log N)$ steps.
- `POST /sync/ast-merge`: Section-aware 3-way AST merge for structured Markdown.
- `POST /sync/ml/analyze-conflict`: ML polarity contradiction and conflict risk scoring.

---

## 5. How Synchronization Works

```mermaid
flowchart TD
    A["Device submits op with base_version"] --> B{"base_version == server.version?"}
    B -- Yes --> C["Fast-forward commit (CAS write)"]
    B -- No --> D{"Load snapshot of base_version"}
    D --> E["Run 3-Way Diff3 Merge"]
    E --> F{"Are there overlapping line conflicts?"}
    F -- No --> G["Merge disjoint edits (Outcome: MERGED)"]
    F -- Yes --> H{"Strategy"}
    H -- "merge / diff3 / manual" --> I["Reject write (Outcome: CONFLICT)"]
    H -- "client_wins" --> J["Force client state as new version"]
    H -- "server_wins" --> K["Retain server state (Outcome: RESOLVED)"]
```

---

## 6. Machine Learning Domain Suite

SyncLab uses scikit-learn and NLP routines for predictive sync management:
1. **Semantic Conflict Detector:** Evaluates sentiment, polarity, and negations across non-overlapping edits to catch logical contradictions.
2. **Conflict Risk Predictor:** Calibrated model computing the probability of conflict ($0.0 \to 1.0$) based on offline duration, edit volume, and Levenshtein divergence.
3. **Smart Merge Synthesizer:** Ranks potential merge strategies by semantic coherence.
4. **Sync Anomaly Detector:** Flags malformed payloads or anomalous synchronization frequencies.

---

## 7. Automated Testing & Verification

SyncLab maintains a **100% test pass rate** across 42 comprehensive tests:

```bash
# Run the test suite
python -m pytest -v
```

```
============================== 42 passed in 1.48s ==============================
```

---

## 8. Community Standards

SyncLab complies strictly with GitHub Community Standards:
- [Code of Conduct](CODE_OF_CONDUCT.md) (Contributor Covenant 2.1)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [License](LICENSE) (MIT)
