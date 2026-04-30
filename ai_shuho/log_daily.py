"""Build daily materials JSON from the logs SQLite DB (simplified, no persona system)."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from .log_db import available_days, connect_month_db, month_db_paths
from .log_util import JST, clean_message_text, ensure_directory, ensure_parent, month_key_for_day_key, parse_timestamp


def _format_clock(ts: str | None) -> str | None:
    parsed = parse_timestamp(ts)
    if parsed is None:
        return None
    return parsed.astimezone(JST).strftime("%H:%M")


def _material_text(text: str | None, limit: int = 700) -> str:
    cleaned = clean_message_text(text or "")
    if len(cleaned) <= limit:
        return cleaned
    suffix = "[TRUNCATED]"
    return cleaned[: max(0, limit - len(suffix))].rstrip() + suffix


def _collect_rows(connection: sqlite3.Connection, day_key: str) -> dict[str, list[sqlite3.Row]]:
    messages = connection.execute(
        """
        SELECT m.*, s.ai_name, s.workspace_path, s.title
        FROM messages m
        JOIN sessions s ON s.session_uid = m.session_uid
        WHERE m.day_key = ?
        ORDER BY m.ts, m.seq
        """,
        (day_key,),
    ).fetchall()
    actions = connection.execute(
        """
        SELECT a.*, s.ai_name, s.workspace_path, s.title
        FROM actions a
        JOIN sessions s ON s.session_uid = a.session_uid
        WHERE a.day_key = ?
        ORDER BY a.ts, a.seq
        """,
        (day_key,),
    ).fetchall()
    return {"messages": messages, "actions": actions}


_NOISE_PROMPT_PREFIXES = (
    "# AGENTS.md",
    "# Global",
    "The user interrupted",
    "The model has been switched",
    "retry",
)


def _is_noise_prompt(text: str) -> bool:
    t = (text or "").strip()
    return t == "retry" or any(t.startswith(p) for p in _NOISE_PROMPT_PREFIXES)


def _summarize_tool_use(text: str) -> str:
    """Convert a raw tool_use content_text into a brief readable string.

    Format: tool_use <id> <ToolName> <rest...>
    Discord reply tool carries the actual sent message in <rest>, so we keep it.
    """
    parts = text.lstrip().split(None, 3)
    if len(parts) < 3:
        return text
    tool_name = parts[2]
    rest = parts[3] if len(parts) > 3 else ""

    if tool_name == "Agent":
        label = rest.split()[0] if rest else ""
        return f"[Agent起動: {label}]"
    elif tool_name == "Skill":
        skill_name = rest.split()[0] if rest else ""
        return f"[Skill: {skill_name}]"
    elif "reply" in tool_name and "discord" in tool_name:
        return rest[:500] if rest else "[Discord返信]"
    elif tool_name in ("Read", "Write", "Edit"):
        path = rest.split()[0] if rest else ""
        filename = path.replace("\\", "/").split("/")[-1]
        return f"[{tool_name}: {filename}]"
    else:
        return f"[{tool_name}]"


def _is_tool_result(msg) -> bool:
    """Return True if this user-role message is a tool result, not a human prompt.

    Claude Code stores tool results with role=user but includes sourceToolAssistantUUID
    in raw_payload to identify them. Other AIs don't use this field.
    """
    raw = msg["raw_payload"]
    if not raw:
        return False
    try:
        return "sourceToolAssistantUUID" in json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False


def _extract_turn_final_replies(actor_messages: list) -> list:
    """Return the final assistant reply for each user turn, grouped by session.

    Skips tool_result messages (role=user with sourceToolAssistantUUID) so that
    tool_use → tool_result cycles within a turn don't split the turn prematurely.
    """
    by_session: dict[str, list] = defaultdict(list)
    for msg in actor_messages:
        by_session[msg["session_uid"]].append(msg)

    final_replies = []
    for msgs in by_session.values():
        msgs_sorted = sorted(msgs, key=lambda m: (m["ts"] or "", m["seq"] or 0))
        current_user = None
        last_text_assistant = None   # テキスト返答あり（優先）
        last_tool_assistant = None   # tool_use のみ（フォールバック）
        for msg in msgs_sorted:
            if msg["role"] == "user":
                if _is_tool_result(msg):
                    continue  # tool_result はターン境界として扱わない
                best = last_text_assistant or last_tool_assistant
                if current_user is not None and best is not None:
                    final_replies.append(best)
                current_user = msg
                last_text_assistant = None
                last_tool_assistant = None
            elif msg["role"] == "assistant":
                text = (msg["content_text"] or "").lstrip()
                if text.startswith("tool_use "):
                    last_tool_assistant = msg
                else:
                    last_text_assistant = msg
        best = last_text_assistant or last_tool_assistant
        if current_user is not None and best is not None:
            final_replies.append(best)
    return final_replies


def _build_actor_materials(rows: dict[str, list[sqlite3.Row]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "session_ids": set(),
        "_messages": [],
        "user_prompts": [],
        "action_count": 0,
        "first_ts": None,
        "last_ts": None,
    })

    for row in rows["messages"]:
        ai_name = row["ai_name"] or "Unknown"
        actor = grouped[ai_name]
        actor["session_ids"].add(row["session_uid"])
        actor["_messages"].append(row)
        if row["role"] == "user" and not _is_tool_result(row):
            text = _material_text(row["content_text"])
            if not _is_noise_prompt(text):
                actor["user_prompts"].append({"time": _format_clock(row["ts"]), "text": text})
        if row["ts"]:
            actor["first_ts"] = row["ts"] if actor["first_ts"] is None else min(actor["first_ts"], row["ts"])
            actor["last_ts"] = row["ts"] if actor["last_ts"] is None else max(actor["last_ts"], row["ts"])

    for row in rows["actions"]:
        ai_name = row["ai_name"] or "Unknown"
        actor = grouped[ai_name]
        actor["session_ids"].add(row["session_uid"])
        actor["action_count"] += 1
        if row["ts"]:
            actor["first_ts"] = row["ts"] if actor["first_ts"] is None else min(actor["first_ts"], row["ts"])
            actor["last_ts"] = row["ts"] if actor["last_ts"] is None else max(actor["last_ts"], row["ts"])

    actors: list[dict[str, Any]] = []
    for ai_name, actor in sorted(grouped.items(), key=lambda x: x[1]["first_ts"] or ""):
        session_count = len(actor["session_ids"])
        action_count = actor["action_count"]
        first = _format_clock(actor["first_ts"])
        last = _format_clock(actor["last_ts"])
        time_window = f"{first}-{last}" if first and last and first != last else first or last or ""
        if session_count <= 2 and action_count <= 8:
            activity_level = "low"
        elif session_count >= 11 or action_count >= 40:
            activity_level = "high"
        else:
            activity_level = "normal"
        final_replies = _extract_turn_final_replies(actor["_messages"])
        assistant_replies = []
        for r in final_replies:
            text = _material_text(r["content_text"])
            if text.lstrip().startswith("tool_use "):
                text = _summarize_tool_use(text)
            assistant_replies.append({"time": _format_clock(r["ts"]), "text": text})
        actors.append({
            "ai_name": ai_name,
            "tag": ai_name,
            "first_person_ja": "",
            "tone_type_ja": "",
            "sentence_structure_ja": "",
            "session_count": session_count,
            "action_count": action_count,
            "activity_level": activity_level,
            "time_window": time_window,
            "user_prompts": actor["user_prompts"],
            "assistant_replies": assistant_replies,
        })
    return actors


def build_daily_materials(connection: sqlite3.Connection, day_key: str, daily_dir: Path) -> Path:
    """Query SQLite, build materials dict, write *-ai-daily-materials.json."""
    ensure_directory(daily_dir)
    rows = _collect_rows(connection, day_key)
    actors = _build_actor_materials(rows)
    materials = {
        "day_key": day_key,
        "day_label": day_key.replace("-", "/"),
        "actors": actors,
    }
    out = daily_dir / f"{day_key}-ai-daily-materials.json"
    out.write_text(json.dumps(materials, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def generate_daily_range(
    db_dir: str,
    daily_dir: Path,
    *,
    from_day: str | None = None,
    to_day: str | None = None,
    missing_only: bool = False,
) -> dict[str, list[str]]:
    """Generate daily materials JSON files for the given day range."""
    all_days = available_days(db_dir)
    selected = all_days
    if from_day:
        selected = [d for d in selected if d >= from_day]
    if to_day:
        selected = [d for d in selected if d <= to_day]

    built: list[str] = []
    skipped: list[str] = []
    month_connections: dict[str, sqlite3.Connection] = {}

    try:
        for day_key in selected:
            out_path = daily_dir / f"{day_key}-ai-daily-materials.json"
            if missing_only and out_path.exists():
                skipped.append(day_key)
                continue
            month_key = month_key_for_day_key(day_key)
            if not month_key:
                continue
            if month_key not in month_connections:
                month_connections[month_key] = connect_month_db(db_dir, month_key)
            build_daily_materials(month_connections[month_key], day_key, daily_dir)
            built.append(day_key)
        for conn in month_connections.values():
            conn.commit()
    finally:
        for conn in month_connections.values():
            conn.close()

    return {"built": built, "skipped": skipped}
