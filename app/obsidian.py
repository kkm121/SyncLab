"""Obsidian Markdown export with YAML frontmatter."""
import json
import yaml


def to_markdown(*args, **kwargs) -> str:
    if len(args) == 1:
        doc = args[0]
        tags = json.loads(getattr(doc, "tags_json", "[]") or "[]") if isinstance(getattr(doc, "tags_json", None), str) else getattr(doc, "tags", [])
        meta = json.loads(getattr(doc, "meta_json", "{}") or "{}") if isinstance(getattr(doc, "meta_json", None), str) else getattr(doc, "meta", {})
        title = getattr(doc, "title", "")
        collection = getattr(doc, "collection", "default")
        version = getattr(doc, "version", 1)
        deleted = getattr(doc, "deleted", False)
        body = getattr(doc, "body", "")
    else:
        doc_id, collection, title, tags, meta, version, updated_at, body = args[:8]
        deleted = False

    frontmatter = {
        "title": title,
        "collection": collection,
        "version": version,
        "deleted": deleted,
        "tags": list(tags) if tags else [],
    }
    if isinstance(meta, dict):
        frontmatter.update(meta)
    fm_str = yaml.dump(frontmatter, sort_keys=False).strip()
    return f"---\n{fm_str}\n---\n\n{body}\n"
