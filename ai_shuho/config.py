"""
Config loader: reads YAML frontmatter from .md config files.
Pure stdlib — no pyyaml.
"""

from __future__ import annotations
import re
from pathlib import Path

# ── defaults ───────────────────────────────────────────────────────────────

SYS_DEFAULTS: dict = {
    "period_unit": "week",
    "period_days": 7,
    "period_start_weekday": "monday",
    "period_start_hour": 3,
    "period_id_format": "YYYY-WNN",
    "draft_output": True,
    "split_enabled": True,
    "split_char_limit": 140,
    "split_header_format": "YYYY/WNN #N [TAG]",
}

WRITING_DEFAULTS: dict = {
    "narrative_approach": "spotlight_contrast",
    "opening_style": "auto",
    "perspective_switches_max": 4,
    "length_target_min": 800,
    "length_target_max": 2000,
}

# ── YAML frontmatter parser ─────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n(.*)", re.DOTALL)
_KV_RE = re.compile(r"^([\w_]+)\s*:\s*(.*)$")


def _cast(raw: str) -> bool | int | str:
    s = raw.strip()
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    try:
        return int(s)
    except ValueError:
        return s.strip('"').strip("'")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (settings_dict, body_text). Both empty/blank if no frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    settings: dict = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        km = _KV_RE.match(line)
        if km:
            raw = km.group(2)
            # only strip inline # comments for unquoted values
            stripped = raw.strip()
            if not (stripped.startswith('"') or stripped.startswith("'")):
                raw = raw.split("#")[0]
            settings[km.group(1)] = _cast(raw)
    return settings, m.group(2)


# ── config loader ───────────────────────────────────────────────────────────

def _load_md(path: Path) -> tuple[dict, str]:
    if path.exists():
        return parse_frontmatter(path.read_text(encoding="utf-8"))
    return {}, ""


def load_system_config(config_dir: Path) -> dict:
    user_cfg, _ = _load_md(config_dir / "system-config.md")
    default_cfg, _ = _load_md(config_dir / "system-config.default.md")
    return {**SYS_DEFAULTS, **default_cfg, **user_cfg}


def load_writing_config(config_dir: Path) -> tuple[dict, str]:
    """Return (settings_dict, prose_body). Prose body goes into writer prompt."""
    user_cfg, user_body = _load_md(config_dir / "writing-config.md")
    default_cfg, default_body = _load_md(config_dir / "writing-config.default.md")

    merged_cfg = {**WRITING_DEFAULTS, **default_cfg, **user_cfg}
    body = user_body.strip() if user_body.strip() else default_body.strip()
    return merged_cfg, body
