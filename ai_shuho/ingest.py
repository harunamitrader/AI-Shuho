"""
Phase 1: Aggregate AI session data from SQLite into a weekly materials JSON.
Reads directly from the SQLite DB (data/logs/db/).
"""

from __future__ import annotations
import json
from pathlib import Path

from .period import period_day_keys, parse_period_key, period_label
from .log_db import connect_month_db
from .log_daily import _collect_rows, _build_actor_materials
from .log_util import month_key_for_day_key


def _weekly_activity_level(total_sessions: int) -> str:
    if total_sessions >= 10:
        return "high"
    if total_sessions >= 3:
        return "normal"
    return "low"


def ingest(period_key: str, db_dir: str, sys_config: dict) -> dict:
    """Aggregate data from SQLite for the period. Returns weekly materials dict."""
    day_keys = period_day_keys(period_key, sys_config)
    start, end = parse_period_key(period_key, sys_config)

    actors_map: dict[str, dict] = {}
    days_loaded: list[str] = []
    month_connections: dict[str, object] = {}

    try:
        for day_key in day_keys:
            month_key = month_key_for_day_key(day_key)
            if not month_key:
                continue
            db_path = Path(db_dir) / f"{month_key}.sqlite"
            if not db_path.exists():
                continue
            if month_key not in month_connections:
                month_connections[month_key] = connect_month_db(db_dir, month_key)
            conn = month_connections[month_key]

            rows = _collect_rows(conn, day_key)
            day_actors = _build_actor_materials(rows)
            if not day_actors:
                continue
            days_loaded.append(day_key)

            for actor in day_actors:
                ai_name = actor["ai_name"]
                if ai_name not in actors_map:
                    actors_map[ai_name] = {
                        "ai_name": ai_name,
                        "tag": actor.get("tag", ai_name),
                        "first_person_ja": actor.get("first_person_ja", ""),
                        "tone_type_ja": actor.get("tone_type_ja", ""),
                        "sentence_structure_ja": actor.get("sentence_structure_ja", ""),
                        "total_sessions": 0,
                        "total_actions": 0,
                        "days_active": 0,
                        "daily_activity": [],
                        "user_prompts": [],
                        "assistant_replies": [],
                    }
                a = actors_map[ai_name]
                a["total_sessions"] += actor["session_count"]
                a["total_actions"] += actor["action_count"]
                a["days_active"] += 1
                a["daily_activity"].append({
                    "day": day_key,
                    "sessions": actor["session_count"],
                    "actions": actor["action_count"],
                    "activity_level": actor["activity_level"],
                    "time_window": actor["time_window"],
                })
                for p in actor.get("user_prompts", []):
                    a["user_prompts"].append({"day": day_key, **p})
                for r in actor.get("assistant_replies", []):
                    a["assistant_replies"].append({"day": day_key, **r})
    finally:
        for conn in month_connections.values():
            conn.close()

    actors = []
    for ai_name, a in actors_map.items():
        a["activity_level"] = _weekly_activity_level(a["total_sessions"])
        actors.append(a)
    actors.sort(key=lambda x: x["total_sessions"], reverse=True)

    return {
        "period_key": period_key,
        "period_label": period_label(period_key, sys_config),
        "period_start": start.strftime("%Y-%m-%d"),
        "period_end": end.strftime("%Y-%m-%d"),
        "day_keys": day_keys,
        "days_loaded": days_loaded,
        "actors": actors,
    }


def save_materials(materials: dict, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"{materials['period_key']}-ai-shuho-materials.json"
    out.write_text(json.dumps(materials, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
