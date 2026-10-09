"""Deterministic 3-way merge over document fields.

Rules (documented, predictable):
- title: scalar 3-way. Changed on one side only -> take it. Changed on
  both sides differently -> conflict.
- tags: set union. Added anywhere is kept. A removal is honored only when
  the other side made no tag changes at all; otherwise union wins.
  Never conflicts.
- meta: recursive per-key 3-way; same leaf changed differently -> conflict
  reported at the dotted key path (e.g. "meta.priority").
- body: line-based 3-way. Edits to disjoint line regions merge; overlapping
  regions conflict with full texts attached.
"""
import difflib
from dataclasses import dataclass, field


@dataclass
class Conflict:
    field: str
    base: object
    mine: object
    current: object


@dataclass
class MergeResult:
    values: dict
    merged_fields: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)


def merge_scalar(fname: str, base, mine, current) -> tuple[object, list[Conflict]]:
    if mine == base:
        return current, []
    if current == base or mine == current:
        return mine, []
    return None, [Conflict(field=fname, base=base, mine=mine, current=current)]


def merge_tags(base: list, mine: list, current: list) -> tuple[list, list]:
    b, m, c = set(base), set(mine), set(current)
    kept: set = set()
    for tag in b | m | c:
        in_b, in_m, in_c = tag in b, tag in m, tag in c
        if in_m and in_c:
            kept.add(tag)  # present on both sides -> kept
        elif in_m and not in_c:
            # Current side deleted it: honor only if mine never touched tags.
            if m != b:
                kept.add(tag)  # union wins, no conflict
        elif in_c and not in_m:
            # Mine deleted it: honor only if current never touched tags.
            if c != b:
                kept.add(tag)
        # absent on both sides -> deleted by both, stays deleted
    return sorted(kept), []


_MISSING = object()


def merge_meta(base: dict, mine: dict, current: dict, prefix="meta") -> tuple[dict, list[Conflict]]:
    merged: dict = {}
    conflicts: list[Conflict] = []
    for key in sorted(set(base) | set(mine) | set(current)):
        path = f"{prefix}.{key}"
        b = base.get(key, _MISSING)
        m = mine.get(key, _MISSING)
        c = current.get(key, _MISSING)
        if m == b:
            if c is _MISSING:
                continue  # deleted by current, untouched by mine
            merged[key] = c
        elif c == b:
            if m is _MISSING:
                continue  # deleted by mine, untouched by current
            merged[key] = m
        elif m == c:
            merged[key] = m  # both sides changed identically
        elif (
            isinstance(b, dict) and isinstance(m, dict) and isinstance(c, dict)
        ):
            sub, sub_c = merge_meta(b, m, c, prefix=path)
            merged[key] = sub
            conflicts.extend(sub_c)
        else:
            # Changed on both sides differently (incl. delete-vs-edit).
            conflicts.append(
                Conflict(
                    field=path,
                    base=None if b is _MISSING else b,
                    mine=None if m is _MISSING else m,
                    current=None if c is _MISSING else c,
                )
            )
    return merged, conflicts


def _regions(base_lines: list[str], new_lines: list[str]):
    sm = difflib.SequenceMatcher(a=base_lines, b=new_lines, autojunk=False)
    return [(a1, a2, b1, b2) for tag, a1, a2, b1, b2 in sm.get_opcodes() if tag != "equal"]


def merge_body(base: str, mine: str, current: str) -> tuple[str | None, list[Conflict]]:
    if mine == base:
        return current, []
    if current == base or mine == current:
        return mine, []
    b_lines = base.splitlines()
    mine_regions = _regions(b_lines, mine.splitlines())
    cur_regions = _regions(b_lines, current.splitlines())
    for ma1, ma2, _, _ in mine_regions:
        for ca1, ca2, _, _ in cur_regions:
            if ma1 < ca2 and ca1 < ma2:  # overlapping base ranges
                return None, [Conflict(field="body", base=base, mine=mine, current=current)]
    edits = [(a1, a2, mine.splitlines()[b1:b2]) for a1, a2, b1, b2 in mine_regions]
    edits += [(a1, a2, current.splitlines()[b1:b2]) for a1, a2, b1, b2 in cur_regions]
    edits.sort(key=lambda e: (e[0], e[1]))
    out: list[str] = []
    pos = 0
    for a1, a2, new in edits:
        out.extend(b_lines[pos:a1])
        out.extend(new)
        pos = a2
    out.extend(b_lines[pos:])
    trailing = "\n" if (mine.endswith("\n") or current.endswith("\n")) else ""
    return "\n".join(out) + (trailing if out else ""), []


def three_way_merge(base: dict, mine: dict, current: dict) -> MergeResult:
    """base/mine/current map field -> value for title/body/tags/meta."""
    values: dict = {}
    merged_fields: list[str] = []
    conflicts: list[Conflict] = []

    for fname in ("title",):
        val, conf = merge_scalar(fname, base.get(fname), mine.get(fname), current.get(fname))
        conflicts.extend(conf)
        if not conf:
            values[fname] = val
            if mine.get(fname) != base.get(fname):
                merged_fields.append(fname)

    tags, tag_conf = merge_tags(base.get("tags", []), mine.get("tags", []), current.get("tags", []))
    conflicts.extend(tag_conf)
    values["tags"] = tags
    if set(mine.get("tags", [])) != set(base.get("tags", [])):
        merged_fields.append("tags")

    meta, meta_conf = merge_meta(
        base.get("meta", {}), mine.get("meta", {}), current.get("meta", {})
    )
    conflicts.extend(meta_conf)
    values["meta"] = meta
    if mine.get("meta", {}) != base.get("meta", {}):
        merged_fields.append("meta")

    body, body_conf = merge_body(
        base.get("body", ""), mine.get("body", ""), current.get("body", "")
    )
    conflicts.extend(body_conf)
    if not body_conf:
        values["body"] = body
        if mine.get("body", "") != base.get("body", ""):
            merged_fields.append("body")

    return MergeResult(values=values, merged_fields=merged_fields, conflicts=conflicts)

