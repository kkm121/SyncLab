# SyncLab — Offline-First Sync With Honest Conflicts

<p align="left">
  <img src="https://img.shields.io/badge/FastAPI-0.142-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/SQLite-file--backed-003B57.svg" alt="SQLite">
  <img src="https://img.shields.io/badge/Tests-pytest-16A34A.svg" alt="pytest">
  <img src="https://img.shields.io/badge/License-MIT-1D4ED8.svg" alt="License MIT">
</p>

**SyncLab** is a backend that synchronizes document edits coming from multiple devices. Every write carries the version the device last saw (`base_version`); stale writes are merged field-by-field or reported as conflicts — never silently overwritten. Built as **Backend Task 2 (Offline Sync Conflict)** for the GDG on Campus SRM Technical Domain recruitments 2026-27. No frontend; demonstrated via Swagger UI, curl, or the included two-device demo script.

---

## Table of Contents

- [1. Repository Structure](#1-repository-structure)
- [2. Setup](#2-setup)
- [3. How Synchronization Works](#3-how-synchronization-works)
- [4. API Endpoints](#4-api-endpoints)
- [5. Conflicting vs Non-Conflicting Scenarios](#5-conflicting-vs-non-conflicting-scenarios)
- [6. Example Session](#6-example-session)
- [7. Assumptions and Design Decisions](#7-assumptions-and-design-decisions)

---

## 1. Repository Structure

```
backend-offline-sync/
├── app/
│   ├── main.py           # App, error envelopes, lifespan, routers
│   ├── config.py         # DATABASE_URL via env
│   ├── db.py             # SQLite engine, sessions, init
│   ├── models.py         # Device, Document, Version (history), AppliedOp (idempotency)
│   ├── schemas.py        # Pydantic models, Strategy/Outcome enums, envelopes
│   ├── sync_engine.py    # Pure 3-way merge: scalars, tag sets, meta dicts, body lines
│   ├── sync_service.py   # execute_op: CAS writes, history rows, op log, strategies
│   ├── obsidian.py       # Markdown + YAML frontmatter exporter
│   └── routers/
│       ├── documents.py  # CRUD, history, restore, export.md
│       ├── sync.py       # POST /sync, POST /sync/batch
│       └── devices.py    # register + catch-up change feed
├── scripts/demo_conflict.py # Laptop-vs-phone narrative (no server needed)
├── tests/                # pytest: protocol, strategies, history, race test
├── requirements.txt
└── LICENSE, CODE_OF_CONDUCT.md, CONTRIBUTING.md, SECURITY.md
```

---

## 2. Setup

Prerequisites: Python 3.11+ and pip.

```bash
git clone <repo-url-shared-later>
cd backend-offline-sync
python -m venv .venv
.\.venv\Scripts\activate        # Windows; use bin/activate on Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000
```

Swagger UI: `http://localhost:8000/docs`. Run tests: `python -m pytest tests/ -q` (16 tests, all passing). Run the demo: `PYTHONPATH=. python scripts/demo_conflict.py`.

---

## 3. How Synchronization Works

Documents carry an integer `version`. Every mutation states its `base_version`:

| Situation | Outcome | What happens |
| :--- | :--- | :--- |
| `base_version == current`, changes present | `accepted` | Fast-forward to v+1, history row written. |
| `base_version == current`, nothing changed | `accepted` | No-op ("already current"), no version bump. |
| `base_version < current`, disjoint edits | `merged` | 3-way merge applied, v+1, `merged_fields` listed. |
| `base_version < current`, same-field edits | `conflict` | Nothing written; `conflicts[]` carries base/mine/current per field. |
| Unknown doc / bad base / deleted / racing write | `rejected` | Nothing written; `resolution` says exactly why + what to do. |
| Same `op_id` sent again | `idempotent_replay` | Stored result returned; state touched once. |

Merge rules (`app/sync_engine.py`): scalars take the side that changed (both-changed-differently conflicts); tags union (a removal counts only if the other side never touched tags); `meta` merges per key with dotted conflict paths (`meta.budget`); `body` merges disjoint line regions via difflib hunks and conflicts on overlap.

Strategies (per request, default `merge`): `merge` writes only when conflict-free; `server_wins` keeps current state without a phantom bump; `client_wins` forces device state as a new version listing overridden fields; `manual` never auto-writes on a stale base. Writes use compare-and-swap on `version`, so two racing requests cannot both commit — the loser gets `rejected` ("refetch and retry").

Extras: full version history with restore-as-new-version (history is never rewritten), soft-delete tombstones, batch queue flush with per-op results, device registry with `since_seq` catch-up feed, tag/text search, and Obsidian export (`export.md`: YAML frontmatter with title, tags, version + Markdown body).

---

## 4. API Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | `/documents` | Direct create (v1). Body: collection, title, body, tags, meta, device_id. |
| GET | `/documents?collection=&tag=&q=` | Search/filter, newest first. |
| GET | `/documents/{id}` | Current state incl. version. |
| POST | `/sync` | One operation (create when `document_id` omitted). 404 only for unknown docs. |
| POST | `/sync/batch` | Offline queue flush (1-100 ops), per-op outcomes. |
| GET | `/documents/{id}/versions` | Full history. |
| GET | `/documents/{id}/versions/{v}` | One snapshot. |
| POST | `/documents/{id}/restore/{v}?device_id=` | Restore as a new version. |
| GET | `/documents/{id}/export.md` | Obsidian-ready Markdown download. |
| POST | `/devices/register` | Register `{device_id, name}`. |
| GET | `/devices/{id}/changes?since_seq=` | Catch-up feed after offline time. |
| GET | `/health`, `/`, `/docs` | Meta and Swagger UI. |

---

## 5. Conflicting vs Non-Conflicting Scenarios

Non-conflicting (merged, nothing lost): laptop renames the title while the phone edits body lines; one side adds a tag while the other edits metadata; two devices append different paragraphs; identical edits on both sides.

Conflicting (returned, never overwritten): both retitle differently; both change `meta.budget` to different values; overlapping body-line edits; any stale write under `manual` strategy. The response includes all three values per field so the client can resolve and resubmit with a fresh base.

Edge cases handled: duplicate sends (idempotency keys), out-of-order arrivals (base checks), unknown/forward bases (rejected with guidance), tombstone edits (rejected until restored), concurrent writers (CAS → loser retries), empty no-op syncs (accepted, no bump).

---

## 6. Example Session

Real output of `scripts/demo_conflict.py` (laptop online, phone offline with v1):

```
Created note id=1 at v1 (laptop). Phone goes offline with v1.

### Laptop renames title (online, v1->v2)
    outcome=accepted v1->v2 merged=['title']

### Phone edits Day 2 from stale v1 (different lines -> MERGED)
    outcome=merged v1->v3 merged=['tags', 'body']

### Phone edits title from stale v1 (same field -> CONFLICT, no overwrite)
    outcome=conflict v1->v3 conflicts=['title']

### Phone resolves with client_wins on fresh base
    outcome=accepted v3->v4 merged=['title']

History: 4 versions, nothing rewritten.
```

curl equivalent of a merge:

```bash
curl -X POST http://localhost:8000/sync -H 'Content-Type: application/json' \
  -d '{"document_id":1,"base_version":1,"body":"Day 1: beach.\nDay 2: scuba.\nDay 3: market.\n","device_id":"phone-1"}'
# {"outcome":"merged","base_version":1,"current_version":3,
#  "merged_fields":["body"], "conflicts":[], ...}
```

---

## 7. Assumptions and Design Decisions

- **SQLite + single-writer CAS**: correct for review scale via compare-and-swap updates; multi-worker production would move to Postgres (same CAS pattern) — stated, not hidden.
- **No auth**: the brief requires none; devices are identified (`device_id`) for audit, not trusted for access. A real deployment would add per-user keys like the WhistleDrop service.
- **Omitted sync fields mean "unchanged from base"**: partial ops merge against the stored base snapshot, which is why full version snapshots are kept.
- **Restore never rewrites history**: it appends a new version, so audits stay truthful.
- **Rejected beats guessing**: unknown docs/bases/versions always explain and point at the refetch, keeping clients in an explicit state machine instead of silent divergence.
- **Render note**: same as WhistleDrop — SQLite file is ephemeral on free tiers; point `DATABASE_URL` at persistent Postgres to keep data.

---

<p align="center">
  <b>SyncLab</b> — GDG on Campus SRM Technical Domain, Backend Task 2<br>
  Stale writes merge or conflict. They never overwrite.
</p>

