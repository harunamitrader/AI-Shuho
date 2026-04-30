"""
Publish validated drafts to final output files.

reads from reports_dir (weekly/), writes final files to publish_dir (published/).
"""

from __future__ import annotations
import json
import shutil
from pathlib import Path


def _posts_json_to_md(posts_data: dict) -> str:
    """Convert posts-draft.json → human-readable markdown thread."""
    lines = []
    period = posts_data.get("period_key", "")
    lines.append(f"# {period} X投稿スレッド\n")
    for post in posts_data.get("posts", []):
        idx = post.get("post_index", "")
        text = post.get("text", "")
        char_count = post.get("char_count", 0)
        lines.append(f"## #{idx} ({char_count}字)\n")
        lines.append(text)
        lines.append("\n---\n")
    return "\n".join(lines)


def publish(
    period_key: str,
    reports_dir: Path,
    sys_config: dict,
    publish_dir: Path | None = None,
) -> list[Path]:
    if publish_dir is None:
        publish_dir = reports_dir
    publish_dir.mkdir(parents=True, exist_ok=True)

    published = []

    draft_md = reports_dir / f"{period_key}-ai-shuho-draft.md"
    final_md = publish_dir / f"{period_key}-ai-shuho.md"
    if draft_md.exists():
        shutil.copy2(draft_md, final_md)
        published.append(final_md)

    if sys_config.get("split_enabled", True):
        draft_posts = reports_dir / f"{period_key}-ai-shuho-posts-draft.json"
        if draft_posts.exists():
            posts_data = json.loads(draft_posts.read_text(encoding="utf-8"))
            final_posts = publish_dir / f"{period_key}-ai-shuho-posts.md"
            final_posts.write_text(_posts_json_to_md(posts_data), encoding="utf-8")
            published.append(final_posts)

    return published
