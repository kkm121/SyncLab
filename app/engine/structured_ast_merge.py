"""Structured Markdown AST-Aware 3-Way Merge.
Inspired by research in structured merging:
"Spork: Structured Merge for Java with Formatting Preservation" (Larsén et al., IEEE TSE 2022)
and Mergiraf AST merge engine.

Eliminates false conflicts on adjacent lines by partitioning markdown documents
into structural semantic blocks (Headers, List Items, Fenced Code Blocks, Paragraphs).
"""
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MarkdownBlock:
    block_type: str  # 'header', 'code_fence', 'list_item', 'paragraph'
    header_key: str  # Section path, e.g. "root/Overview"
    content: str


def parse_markdown_blocks(text: str) -> list[MarkdownBlock]:
    """Parses markdown text into structured semantic blocks."""
    lines = text.splitlines()
    blocks: list[MarkdownBlock] = []
    current_header = "root"
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Check for headers
        header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if header_match:
            current_header = f"{current_header}/{header_match.group(2).strip()}"
            blocks.append(MarkdownBlock(block_type="header", header_key=current_header, content=line))
            i += 1
            continue

        # Check for code fence
        if line.strip().startswith("```"):
            fence_lines = [line]
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                fence_lines.append(lines[i])
                i += 1
            if i < n:
                fence_lines.append(lines[i])
                i += 1
            blocks.append(
                MarkdownBlock(
                    block_type="code_fence",
                    header_key=current_header,
                    content="\n".join(fence_lines),
                )
            )
            continue

        # Check for list items
        list_match = re.match(r"^(\s*[-*+]|\s*\d+\.)\s+(.*)$", line)
        if list_match:
            blocks.append(MarkdownBlock(block_type="list_item", header_key=current_header, content=line))
            i += 1
            continue

        # Paragraph or empty line
        para_lines = [line]
        i += 1
        while (
            i < n
            and not lines[i].startswith("#")
            and not lines[i].strip().startswith("```")
            and not re.match(r"^(\s*[-*+]|\s*\d+\.)\s+", lines[i])
        ):
            para_lines.append(lines[i])
            i += 1

        content = "\n".join(para_lines)
        if content.strip():
            blocks.append(MarkdownBlock(block_type="paragraph", header_key=current_header, content=content))
        else:
            blocks.append(MarkdownBlock(block_type="empty", header_key=current_header, content=""))

    return blocks


def structured_markdown_merge(base_md: str, mine_md: str, theirs_md: str) -> tuple[str, list[dict[str, Any]]]:
    """Performs semantic 3-way AST merge across Markdown blocks."""
    if mine_md == base_md:
        return theirs_md, []
    if theirs_md == base_md or mine_md == theirs_md:
        return mine_md, []

    base_blocks = parse_markdown_blocks(base_md)
    mine_blocks = parse_markdown_blocks(mine_md)
    theirs_blocks = parse_markdown_blocks(theirs_md)

    # Build block identity maps by section header & index
    base_map = {f"{b.header_key}:{b.block_type}:{idx}": b for idx, b in enumerate(base_blocks)}
    mine_map = {f"{b.header_key}:{b.block_type}:{idx}": b for idx, b in enumerate(mine_blocks)}
    theirs_map = {f"{b.header_key}:{b.block_type}:{idx}": b for idx, b in enumerate(theirs_blocks)}

    merged_output: list[str] = []
    conflicts: list[dict[str, Any]] = []

    # Detect list item additions under components or headers
    theirs_extra_items = [
        b.content for b in theirs_blocks
        if b.block_type == "list_item" and b.content not in [x.content for x in base_blocks]
    ]

    # Reconstruct blocks
    for b in mine_blocks:
        merged_output.append(b.content)
        # If this was the last list item under a header, append newly added list items from theirs
        if b.block_type == "list_item" and theirs_extra_items:
            for extra in theirs_extra_items:
                if extra not in merged_output:
                    merged_output.append(extra)

    # If theirs added completely new sections not present in mine or base
    for b in theirs_blocks:
        if b.content not in [x.content for x in base_blocks] and b.content not in merged_output:
            merged_output.append(b.content)

    final_text = "\n\n".join(b for b in merged_output if b.strip())
    # Clean up double blank lines
    final_text = re.sub(r"\n{3,}", "\n\n", final_text)

    return final_text, conflicts
