"""Single place where state changes happen: CAS writes, history, op log."""
import json
from sqlalchemy import update

from . import sync_engine as eng
from .models import AppliedOp, Document, Version
from .schemas import (
    ConflictOut,
    DocumentOut,
    Outcome,
    Strategy,
    SyncOp,
    SyncResult,
)


def doc_to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        collection=doc.collection,
        title=doc.title,
        body=doc.body,
        tags=json.loads(doc.tags_json or "[]"),
        meta=json.loads(doc.meta_json or "{}"),
        version=doc.version,
        deleted=doc.deleted,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def snapshot_of(doc: Document) -> dict:
    return {
        "title": doc.title,
        "body": doc.body,
        "tags": json.loads(doc.tags_json or "[]"),
        "meta": json.loads(doc.meta_json or "{}"),
    }


def record_version(db, doc: Document, device_id: str, strategy: str, outcome: str) -> None:
    snap = snapshot_of(doc)
    db.add(
        Version(
            document_id=doc.id,
            version=doc.version,
            title=snap["title"],
            body=snap["body"],
            tags_json=json.dumps(snap["tags"], ensure_ascii=False),
            meta_json=json.dumps(snap["meta"], ensure_ascii=False),
            deleted=doc.deleted,
            device_id=device_id,
            strategy=strategy,
            outcome=outcome,
        )
    )


def _store_op(db, op_id: str | None, result: SyncResult) -> None:
    if not op_id:
        return
    db.add(AppliedOp(op_id=op_id, result_json=result.model_dump_json()))
    db.commit()


def _replay(db, op_id: str) -> SyncResult | None:
    row = db.query(AppliedOp).filter_by(op_id=op_id).first()
    if not row:
        return None
    prior = SyncResult.model_validate_json(row.result_json)
    prior.outcome = Outcome.idempotent_replay
    return prior


def execute_op(db, op: SyncOp) -> SyncResult:
    """Apply one sync operation. Never silently overwrites newer state."""
    if op.op_id:
        replay = _replay(db, op.op_id)
        if replay:
            return replay

    def finish(result: SyncResult) -> SyncResult:
        _store_op(db, op.op_id, result)
        try:
            from .engine.realtime_hub import hub
            hub.broadcast(
                f"SYNC_{result.outcome.value.upper()}",
                {
                    "device_id": op.device_id,
                    "document_id": op.document_id or (result.document.id if result.document else None),
                    "base_version": op.base_version,
                    "current_version": result.current_version,
                    "outcome": result.outcome.value,
                    "strategy": op.strategy.value if op.strategy else None,
                    "merged_fields": result.merged_fields,
                    "conflicts": [c.model_dump() for c in result.conflicts] if result.conflicts else [],
                    "resolution": result.resolution,
                },
            )
        except Exception:
            pass
        return result

    # ---- create path ----
    if op.document_id is None:
        doc = Document(
            collection=op.collection,
            title=op.title or "",
            body=op.body or "",
            tags_json=json.dumps(op.tags or [], ensure_ascii=False),
            meta_json=json.dumps(op.meta or {}, ensure_ascii=False),
            version=1,
            deleted=bool(op.delete),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        record_version(db, doc, op.device_id, op.strategy.value, "accepted")
        db.commit()
        return finish(
            SyncResult(
                outcome=Outcome.accepted,
                document=doc_to_out(doc),
                base_version=0,
                current_version=1,
            )
        )

    doc = db.query(Document).filter_by(id=op.document_id).first()
    if not doc:
        return finish(
            SyncResult(
                outcome=Outcome.rejected,
                document=None,
                base_version=op.base_version,
                current_version=0,
                resolution=f"Unknown document {op.document_id}.",
            )
        )
    if doc.deleted and not op.delete:
        return finish(
            SyncResult(
                outcome=Outcome.rejected,
                document=doc_to_out(doc),
                base_version=op.base_version,
                current_version=doc.version,
                resolution=f"Document is deleted (tombstone v{doc.version}); restore it before editing.",
            )
        )
    if op.base_version > doc.version:
        return finish(
            SyncResult(
                outcome=Outcome.rejected,
                document=doc_to_out(doc),
                base_version=op.base_version,
                current_version=doc.version,
                resolution="Base version is ahead of the server; refetch before syncing.",
            )
        )

    # ---- fast-forward: device was up to date ----
    if op.base_version == doc.version:
        before = snapshot_of(doc)
        if op.delete:
            doc.deleted = True
        changed = _apply_partial(doc, op) or bool(op.delete)
        if not changed:
            return finish(
                SyncResult(
                    outcome=Outcome.accepted,
                    document=doc_to_out(doc),
                    base_version=op.base_version,
                    current_version=doc.version,
                    resolution="No changes; already current.",
                )
            )
        after = snapshot_of(doc)
        merged = [f for f in ("title", "body", "tags", "meta") if after[f] != before[f]]
        if bool(op.delete):
            merged.append("deleted")
        return finish(
            _commit_new_version(db, doc, op, "direct", "accepted", merged)
        )

    # ---- stale base: load the snapshot the device edited ----
    base_row = (
        db.query(Version)
        .filter_by(document_id=doc.id, version=op.base_version)
        .first()
    )
    if not base_row:
        return finish(
            SyncResult(
                outcome=Outcome.rejected,
                document=doc_to_out(doc),
                base_version=op.base_version,
                current_version=doc.version,
                resolution=f"Unknown base version {op.base_version}; refetch version {doc.version}.",
            )
        )
    base = {
        "title": base_row.title,
        "body": base_row.body,
        "tags": json.loads(base_row.tags_json or "[]"),
        "meta": json.loads(base_row.meta_json or "{}"),
    }
    mine = dict(base)
    if op.title is not None:
        mine["title"] = op.title
    if op.body is not None:
        mine["body"] = op.body
    if op.tags is not None:
        mine["tags"] = list(op.tags)
    if op.meta is not None:
        mine["meta"] = dict(op.meta)
    current = snapshot_of(doc)

    result = eng.three_way_merge(base, mine, current)
    conflicts = [
        ConflictOut(field=c.field, base=c.base, mine=c.mine, current=c.current)
        for c in result.conflicts
    ]

    strategy = op.strategy
    if strategy == Strategy.manual:
        return finish(
            SyncResult(
                outcome=Outcome.conflict,
                document=doc_to_out(doc),
                base_version=op.base_version,
                current_version=doc.version,
                merged_fields=result.merged_fields,
                conflicts=conflicts,
                resolution="Manual strategy: resubmit with fresh base_version after resolving.",
            )
        )
    if result.conflicts and strategy == Strategy.merge:
        return finish(
            SyncResult(
                outcome=Outcome.conflict,
                document=doc_to_out(doc),
                base_version=op.base_version,
                current_version=doc.version,
                merged_fields=result.merged_fields,
                conflicts=conflicts,
                resolution="Same-field edits on both sides; resolve and resubmit.",
            )
        )
    if result.conflicts and strategy == Strategy.server_wins:
        dropped = sorted({c.field for c in result.conflicts} | set(result.merged_fields))
        return finish(
            SyncResult(
                outcome=Outcome.resolved,
                document=doc_to_out(doc),
                base_version=op.base_version,
                current_version=doc.version,
                conflicts=conflicts,
                resolution=f"Server state kept at v{doc.version}; dropped device edits to: {dropped}.",
            )
        )
    if strategy == Strategy.client_wins:
        overridden = [f for f in ("title", "body", "tags", "meta") if mine.get(f) != current.get(f)]
        _apply_values(doc, mine)
        if op.delete:
            doc.deleted = True
        return finish(
            _commit_new_version(
                db,
                doc,
                op,
                "client_wins",
                "resolved",
                overridden,
                extra=f"Device state forced over v{doc.version - 1}; overridden: {overridden}.",
            )
        )
    # clean merge
    _apply_values(doc, result.values)
    if op.delete:
        doc.deleted = True
    return finish(
        _commit_new_version(
            db, doc, op, "merge", "merged", result.merged_fields
        )
    )


def _apply_partial(doc: Document, op: SyncOp) -> bool:
    changed = False
    if op.title is not None and op.title != doc.title:
        doc.title = op.title
        changed = True
    if op.body is not None and op.body != doc.body:
        doc.body = op.body
        changed = True
    if op.tags is not None and list(op.tags) != json.loads(doc.tags_json or "[]"):
        doc.tags_json = json.dumps(list(op.tags), ensure_ascii=False)
        changed = True
    if op.meta is not None and dict(op.meta) != json.loads(doc.meta_json or "{}"):
        doc.meta_json = json.dumps(dict(op.meta), ensure_ascii=False)
        changed = True
    return changed


def _apply_values(doc: Document, values: dict) -> None:
    doc.title = values.get("title", doc.title)
    doc.body = values.get("body", doc.body)
    if "tags" in values:
        doc.tags_json = json.dumps(values["tags"], ensure_ascii=False)
    if "meta" in values:
        doc.meta_json = json.dumps(values["meta"], ensure_ascii=False)


def _commit_new_version(
    db, doc: Document, op: SyncOp, strategy: str, outcome: str, merged: list[str], extra: str = ""
) -> SyncResult:
    """Compare-and-swap write: only commits if version is still what we saw."""
    expected = doc.version
    new_version = expected + 1
    rowcount = (
        db.query(Document)
        .filter_by(id=doc.id, version=expected)
        .update(
            {
                "title": doc.title,
                "body": doc.body,
                "tags_json": doc.tags_json,
                "meta_json": doc.meta_json,
                "deleted": doc.deleted,
                "version": new_version,
            },
            synchronize_session=False,
        )
    )
    if rowcount == 0:
        db.rollback()
        fresh = db.query(Document).filter_by(id=doc.id).first()
        return SyncResult(
            outcome=Outcome.rejected,
            document=doc_to_out(fresh),
            base_version=op.base_version,
            current_version=fresh.version,
            resolution="A concurrent write landed first; refetch and retry.",
        )
    db.commit()
    db.refresh(doc)
    record_version(db, doc, op.device_id, strategy, outcome)
    db.commit()
    db.refresh(doc)
    return SyncResult(
        outcome=Outcome(outcome),  # type: ignore[arg-type]
        document=doc_to_out(doc),
        base_version=op.base_version,
        current_version=doc.version,
        merged_fields=merged,
        resolution=extra,
    )

