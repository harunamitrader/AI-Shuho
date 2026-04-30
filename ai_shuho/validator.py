"""
Phase 5a: Validate draft.md and posts-draft.json.

FIX-5: char_count is auto-corrected rather than reported as an error.
"""

from __future__ import annotations
import json
import re
from pathlib import Path


def _check_draft(draft_text: str, writing_cfg: dict) -> list[str]:
    errors = []
    min_chars = int(writing_cfg.get("length_target_min", 400))

    body = re.sub(r"(?m)^##\s+.*作業記録.*$", "", draft_text)
    body = re.sub(r"\|.*\|", "", body)
    body_chars = len(body.strip())

    if body_chars < min_chars:
        errors.append(f"本文が短すぎます: {body_chars}字 (最低 {min_chars}字)")

    if not re.search(r"\|\s*AI\s*\|", draft_text):
        errors.append("作業記録ブロックが見つかりません（| AI | 行がない）")

    return errors


def _fix_and_check_posts(posts_data: dict, sys_config: dict) -> tuple[list[str], list[str], bool]:
    """Returns (errors, warnings, was_corrected)."""
    errors = []
    warnings = []
    char_limit = int(sys_config.get("split_char_limit", 140))
    posts = posts_data.get("posts", [])
    corrected = False

    for p in posts:
        idx = p.get("post_index")
        text = p.get("text", "")
        actual = len(text)

        # FIX-5: auto-correct char_count instead of failing
        if p.get("char_count", -1) != actual:
            warnings.append(f"post #{idx}: char_count を {p.get('char_count')} -> {actual} に自動補正")
            p["char_count"] = actual
            corrected = True

        if actual > char_limit:
            errors.append(f"post #{idx}: {actual}字 > {char_limit}字上限")

    indices = [p.get("post_index") for p in posts]
    expected = list(range(1, len(posts) + 1))
    if indices != expected:
        errors.append(f"post_index が連番でない: {indices}")

    return errors, warnings, corrected


def validate(
    period_key: str,
    reports_dir: Path,
    sys_config: dict,
    writing_cfg: dict,
) -> dict:
    result: dict = {"period_key": period_key, "ok": True, "errors": [], "warnings": []}

    draft_path = reports_dir / f"{period_key}-ai-shuho-draft.md"
    if not draft_path.exists():
        result["errors"].append(f"draft.md が見つかりません: {draft_path}")
        result["ok"] = False
        return result

    result["errors"].extend(_check_draft(draft_path.read_text(encoding="utf-8"), writing_cfg))

    if sys_config.get("split_enabled", True):
        posts_path = reports_dir / f"{period_key}-ai-shuho-posts-draft.json"
        if not posts_path.exists():
            result["errors"].append(f"posts-draft.json が見つかりません: {posts_path}")
        else:
            posts_data = json.loads(posts_path.read_text(encoding="utf-8"))
            errors, warnings, corrected = _fix_and_check_posts(posts_data, sys_config)
            result["errors"].extend(errors)
            result["warnings"].extend(warnings)
            if corrected:
                posts_path.write_text(json.dumps(posts_data, ensure_ascii=False, indent=2), encoding="utf-8")

    result["ok"] = len(result["errors"]) == 0
    return result


def save_validation(result: dict, period_key: str, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"{period_key}-ai-shuho-validation.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
