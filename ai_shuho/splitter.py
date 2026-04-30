"""
Phase 4: Split the long-form draft.md into X-ready posts-draft.json.

Split rules:
- Post #1: work record summary (auto-generated from the ## 作業記録 table)
- Post #2+: narrative body split at paragraph/sentence boundaries
- Each post: header_line + newline + body ≤ split_char_limit
"""

from __future__ import annotations
import json
import re
from pathlib import Path

from .period import format_period_display


def _make_header(period_key: str, post_index: int, tag: str, fmt: str) -> str:
    display = format_period_display(period_key)
    h = fmt.replace("YYYY/WNN", display).replace("YYYY-WNN", period_key)
    h = h.replace("#N", f"#{post_index}")
    if tag:
        h = h.replace("[TAG]", f"[{tag}]")
    else:
        h = re.sub(r"\s*\[TAG\]", "", h)
    return h.strip()


def _table_to_summary(table_lines: list[str]) -> str:
    """Convert markdown table rows to compact summary text."""
    rows = []
    for line in table_lines:
        line = line.strip()
        if not line or line.startswith("|--") or line.startswith("| AI"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append(f"{cells[0]}:{cells[1]}セッション")
    return "　".join(rows) if rows else ""


def _split_at_sentences(text: str, max_chars: int) -> list[str]:
    """Split text at sentence boundaries (。) to fit within max_chars."""
    chunks = []
    current = ""
    # split on 。 keeping delimiter
    parts = re.split(r"(。)", text)
    i = 0
    while i < len(parts):
        segment = parts[i]
        if i + 1 < len(parts) and parts[i + 1] == "。":
            segment += "。"
            i += 2
        else:
            i += 1
        if not segment:
            continue
        if len(current) + len(segment) <= max_chars:
            current += segment
        else:
            if current:
                chunks.append(current.strip())
            current = segment
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text[:max_chars]]


def split_draft(
    draft_text: str,
    period_key: str,
    sys_config: dict,
) -> list[dict]:
    char_limit = int(sys_config.get("split_char_limit", 140))
    header_fmt = str(sys_config.get("split_header_format", "YYYY/WNN #N [TAG]"))

    posts = []
    post_index = 1

    lines = draft_text.splitlines()

    # ── Extract work record table ────────────────────────────────────────────
    table_lines: list[str] = []
    body_start = 0
    in_table_section = False
    for i, line in enumerate(lines):
        if re.match(r"^##\s+.*作業記録", line):
            in_table_section = True
            continue
        if in_table_section:
            if line.startswith("|"):
                table_lines.append(line)
            elif table_lines and not line.strip():
                body_start = i + 1
                break
            elif table_lines:
                body_start = i
                break

    # Post #1: work record summary
    summary = _table_to_summary(table_lines)
    if not summary:
        label = period_key
        summary = f"{label} 作業記録"

    header1 = _make_header(period_key, 1, "作業記録", header_fmt)
    full1 = f"{header1}\n{summary}"
    # truncate if over limit
    if len(full1) > char_limit:
        avail = char_limit - len(header1) - 1
        summary = summary[:avail]
        full1 = f"{header1}\n{summary}"
    posts.append({
        "post_index": 1,
        "kind": "summary",
        "body": summary,
        "char_count": len(full1),
        "text": full1,
    })
    post_index = 2

    # ── Extract narrative body ───────────────────────────────────────────────
    body_lines = lines[body_start:] if body_start else lines
    # skip leading blank lines and any remaining ## headings from work record
    while body_lines and (not body_lines[0].strip() or body_lines[0].startswith("##")):
        body_lines = body_lines[1:]

    # group into paragraphs (split on blank lines)
    paragraphs: list[str] = []
    current_para: list[str] = []
    for line in body_lines:
        if line.strip():
            current_para.append(line)
        else:
            if current_para:
                paragraphs.append("\n".join(current_para))
                current_para = []
    if current_para:
        paragraphs.append("\n".join(current_para))

    # Pack paragraphs into posts
    for para in paragraphs:
        if not para.strip():
            continue
        header = _make_header(period_key, post_index, "", header_fmt)
        avail = char_limit - len(header) - 1  # -1 for the newline

        if len(para) <= avail:
            full = f"{header}\n{para}"
            posts.append({
                "post_index": post_index,
                "kind": "story",
                "body": para,
                "char_count": len(full),
                "text": full,
            })
            post_index += 1
        else:
            # split at sentence boundaries
            chunks = _split_at_sentences(para, avail)
            for chunk in chunks:
                header = _make_header(period_key, post_index, "", header_fmt)
                avail = char_limit - len(header) - 1
                body = chunk[:avail]
                full = f"{header}\n{body}"
                posts.append({
                    "post_index": post_index,
                    "kind": "story",
                    "body": body,
                    "char_count": len(full),
                    "text": full,
                })
                post_index += 1

    return posts


def save_posts_draft(
    posts: list[dict],
    period_key: str,
    materials: dict,
    reports_dir: Path,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_data = {
        "period_key": period_key,
        "period": f"{materials.get('period_start', '')}〜{materials.get('period_end', '')}",
        "posts": posts,
    }
    out = reports_dir / f"{period_key}-ai-shuho-posts-draft.json"
    out.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
