"""
Noise removal: strips internal/system metadata from weekly materials
before passing to an LLM.

Keeps all actual content (user requests, AI replies, meaningful actions).
Removes: system-injected prompts, internal action types, output_paths.
Does NOT regex-strip UUIDs or paths from inside text strings (too risky).
"""

from __future__ import annotations
import json
from pathlib import Path

NOISE_ACTION_NAMES = {
    "task_started", "task_complete", "token_count", "turn_context",
    "reasoning", "system", "user_message",
}

NOISE_PROMPT_PREFIXES = (
    "# AGENTS.md",
    "# Global",
    "The user interrupted",
    "The model has been switched",
    "retry",
)


def _is_noise_prompt(text: str) -> bool:
    t = text.strip()
    return any(t.startswith(p) for p in NOISE_PROMPT_PREFIXES) or t == "retry"


def clean_actor(actor: dict) -> dict:
    a = dict(actor)

    a["user_prompts"] = [
        p for p in actor.get("user_prompts", [])
        if not _is_noise_prompt(p.get("text", ""))
    ]

    a["key_actions"] = [
        act for act in actor.get("key_actions", [])
        if act.get("name", "") not in NOISE_ACTION_NAMES
    ]

    # assistant_replies: keep as-is (all signal)
    return a


def clean_materials(materials: dict) -> dict:
    cleaned = {k: v for k, v in materials.items() if k != "output_paths"}
    cleaned["actors"] = [clean_actor(a) for a in materials.get("actors", [])]
    return cleaned


def run_clean(period_key: str, reports_dir: Path) -> tuple[Path, dict]:
    src = reports_dir / f"{period_key}-ai-shuho-materials.json"
    if not src.exists():
        raise FileNotFoundError(f"materials not found: {src}\nRun 'ingest' first.")

    materials = json.loads(src.read_text(encoding="utf-8"))
    cleaned = clean_materials(materials)

    out = reports_dir / f"{period_key}-ai-shuho-cleaned-materials.json"
    out.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, cleaned


def removal_summary(original: dict, cleaned: dict) -> str:
    lines = []
    for orig, cln in zip(original.get("actors", []), cleaned.get("actors", [])):
        name = orig["ai_name"]
        up_diff = len(orig.get("user_prompts", [])) - len(cln.get("user_prompts", []))
        ka_diff = len(orig.get("key_actions", [])) - len(cln.get("key_actions", []))
        if up_diff or ka_diff:
            lines.append(f"  {name}: prompts -{up_diff}, actions -{ka_diff}")
    return "\n".join(lines) if lines else "  (nothing removed)"
