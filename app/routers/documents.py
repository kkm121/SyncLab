"""Documents: direct CRUD plus history, restore, and Obsidian export."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Document, Version
from ..obsidian import to_markdown
from ..schemas import DocumentCreate, DocumentOut, ErrorBody, VersionOut
from ..sync_service import doc_to_out, record_version

router = APIRouter(tags=["documents"])


def _get_or_404(db: Session, doc_id: int) -> Document:
    doc = db.query(Document).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                error=f"No document with id {doc_id}.", code="unknown_document"
            ).model_dump(),
        )
    return doc


@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentCreate, db: Session = Depends(get_db)):
    doc = Document(
        collection=body.collection,
        title=body.title,
        body=body.body,
        tags_json=json.dumps(body.tags, ensure_ascii=False),
        meta_json=json.dumps(body.meta, ensure_ascii=False),
        version=1,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    record_version(db, doc, body.device_id, "direct", "accepted")
    db.commit()
    db.refresh(doc)
    return doc_to_out(doc)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    collection: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    include_deleted: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    docs = db.query(Document).order_by(Document.id.desc())
    if collection:
        docs = docs.filter_by(collection=collection)
    if not include_deleted:
        docs = docs.filter_by(deleted=False)
    out = []
    for d in docs.offset(offset).limit(limit * 4).all():
        dto = doc_to_out(d)
        if tag and tag not in dto.tags:
            continue
        if q and q.lower() not in (dto.title + "\n" + dto.body).lower():
            continue
        out.append(dto)
        if len(out) >= limit:
            break
    return out


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    return doc_to_out(_get_or_404(db, doc_id))


@router.get("/documents/{doc_id}/versions", response_model=list[VersionOut])
def list_versions(doc_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, doc_id)
    rows = db.query(Version).filter_by(document_id=doc_id).order_by(Version.version).all()
    return [
        VersionOut(
            version=v.version, title=v.title, body=v.body,
            tags=json.loads(v.tags_json or "[]"), meta=json.loads(v.meta_json or "{}"),
            deleted=v.deleted, device_id=v.device_id, strategy=v.strategy,
            outcome=v.outcome, created_at=v.created_at,
        )
        for v in rows
    ]


@router.get("/documents/{doc_id}/versions/{version}", response_model=VersionOut)
def get_version(doc_id: int, version: int, db: Session = Depends(get_db)):
    _get_or_404(db, doc_id)
    v = db.query(Version).filter_by(document_id=doc_id, version=version).first()
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                error=f"No version {version} for document {doc_id}.",
                code="unknown_version",
            ).model_dump(),
        )
    return VersionOut(
        version=v.version, title=v.title, body=v.body,
        tags=json.loads(v.tags_json or "[]"), meta=json.loads(v.meta_json or "{}"),
        deleted=v.deleted, device_id=v.device_id, strategy=v.strategy,
        outcome=v.outcome, created_at=v.created_at,
    )


@router.post("/documents/{doc_id}/restore/{version}", response_model=DocumentOut)
def restore_version(doc_id: int, version: int, device_id: str = "client", db: Session = Depends(get_db)):
    doc = _get_or_404(db, doc_id)
    v = db.query(Version).filter_by(document_id=doc_id, version=version).first()
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                error=f"No version {version} for document {doc_id}.",
                code="unknown_version",
            ).model_dump(),
        )
    # Restore writes a NEW version; history is never rewritten.
    doc.title, doc.body = v.title, v.body
    doc.tags_json, doc.meta_json = v.tags_json, v.meta_json
    doc.deleted = v.deleted
    doc.version += 1
    db.commit()
    db.refresh(doc)
    record_version(db, doc, device_id, "restore", "accepted")
    db.commit()
    db.refresh(doc)
    return doc_to_out(doc)


@router.get("/documents/{doc_id}/export.md")
def export_markdown(doc_id: int, db: Session = Depends(get_db)):
    doc = _get_or_404(db, doc_id)
    if doc.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                error="Document is deleted; restore it to export.",
                code="deleted_document",
            ).model_dump(),
        )
    dto = doc_to_out(doc)
    md = to_markdown(
        dto.id, dto.collection, dto.title, dto.tags, dto.meta,
        dto.version, dto.updated_at.isoformat(), dto.body,
    )
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in (dto.title or f"doc-{dto.id}"))[:60]
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe}-v{dto.version}.md"'},
    )

