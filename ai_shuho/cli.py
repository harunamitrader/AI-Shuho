"""
CLI entry point for ai_shuho.

Commands:
  logs-ingest     Ingest raw AI logs → SQLite DB
  ingest          Aggregate SQLite logs → weekly-materials.json
  clean-materials Remove noise from weekly-materials.json → cleaned-materials.json
  split-for-x     Split draft.md → posts-draft.json
  validate        Validate draft + posts
  publish         Copy drafts to final output files
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def _resolve_dirs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    base = Path(args.base_dir) if hasattr(args, "base_dir") and args.base_dir else Path.cwd()
    config_dir = Path(args.config_dir) if args.config_dir else base / "config"
    reports_dir = Path(args.reports_dir) if args.reports_dir else base / "reports" / "weekly"
    return base, config_dir, reports_dir


def _load_configs(config_dir: Path):
    from .config import load_system_config, load_writing_config
    sys_cfg = load_system_config(config_dir)
    writing_cfg, writing_body = load_writing_config(config_dir)
    return sys_cfg, writing_cfg, writing_body


def cmd_ingest(args: argparse.Namespace) -> None:
    from .ingest import ingest, save_materials

    base, config_dir, reports_dir = _resolve_dirs(args)
    sys_cfg, _, _ = _load_configs(config_dir)

    if getattr(args, "db_dir", None):
        db_dir = str(Path(args.db_dir))
    else:
        log_cfg = _load_log_sources_config(config_dir, base)
        db_dir = log_cfg["paths"]["db_dir"]

    print(f"Ingesting {args.period} from {db_dir} ...")
    materials = ingest(args.period, db_dir, sys_cfg)
    out = save_materials(materials, reports_dir)
    print(f"Saved: {out}")
    print(f"  Days loaded: {materials['days_loaded']}")
    print(f"  Actors: {[a['ai_name'] for a in materials['actors']]}")



def cmd_split_for_x(args: argparse.Namespace) -> None:
    from .splitter import split_draft, save_posts_draft

    _, config_dir, reports_dir = _resolve_dirs(args)
    sys_cfg, _, _ = _load_configs(config_dir)

    draft_path = reports_dir / f"{args.period}-ai-shuho-draft.md"
    if not draft_path.exists():
        print(f"ERROR: draft not found: {draft_path}", file=sys.stderr)
        sys.exit(1)

    # prefer cleaned materials for period metadata
    for suffix in ("cleaned-materials", "materials"):
        mp = reports_dir / f"{args.period}-ai-shuho-{suffix}.json"
        if mp.exists():
            materials = json.loads(mp.read_text(encoding="utf-8"))
            break
    else:
        materials = {}

    draft_text = draft_path.read_text(encoding="utf-8")
    posts = split_draft(draft_text, args.period, sys_cfg)
    out = save_posts_draft(posts, args.period, materials, reports_dir)
    print(f"Saved: {out}")
    print(f"  Posts: {len(posts)}")
    over = [p for p in posts if p["char_count"] > sys_cfg.get("split_char_limit", 140)]
    if over:
        print(f"  WARNING: {len(over)} post(s) exceed char limit", file=sys.stderr)


def cmd_validate(args: argparse.Namespace) -> None:
    from .validator import validate, save_validation

    _, config_dir, reports_dir = _resolve_dirs(args)
    sys_cfg, writing_cfg, _ = _load_configs(config_dir)

    result = validate(args.period, reports_dir, sys_cfg, writing_cfg)
    out = save_validation(result, args.period, reports_dir)
    print(f"Saved: {out}")

    if result["ok"]:
        print("OK - validation passed.")
    else:
        print("FAILED - errors:", file=sys.stderr)
        for e in result["errors"]:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)


def cmd_publish(args: argparse.Namespace) -> None:
    from .publisher import publish

    base, config_dir, reports_dir = _resolve_dirs(args)
    sys_cfg, _, _ = _load_configs(config_dir)

    publish_dir = Path(args.publish_dir) if getattr(args, "publish_dir", None) else None

    published = publish(args.period, reports_dir, sys_cfg, publish_dir=publish_dir)
    if not published:
        print("Nothing to publish (drafts not found).", file=sys.stderr)
        sys.exit(1)
    for p in published:
        print(f"Published: {p}")


def cmd_list_periods(args: argparse.Namespace) -> None:
    from .log_db import available_days
    from datetime import date, timedelta

    base = Path(args.base_dir) if getattr(args, "base_dir", None) else Path.cwd()
    config_dir = Path(args.config_dir) if getattr(args, "config_dir", None) else base / "config"
    log_cfg = _load_log_sources_config(config_dir, base)
    db_dir = log_cfg["paths"]["db_dir"]

    days = available_days(db_dir)
    if not days:
        print("No data found in SQLite DB.")
        return

    # group by ISO week
    weeks: dict[str, list[str]] = {}
    for day_key in days:
        d = date.fromisoformat(day_key)
        iso = d.isocalendar()
        period_key = f"{iso.year}-W{iso.week:02d}"
        weeks.setdefault(period_key, []).append(day_key)

    print(f"DB: {db_dir}")
    print(f"Available periods ({len(weeks)} weeks):")
    for period_key in sorted(weeks):
        day_list = sorted(weeks[period_key])
        print(f"  {period_key}  ({day_list[0]} ~ {day_list[-1]}, {len(day_list)} days)")


def _load_log_sources_config(config_dir: Path, base_dir: Path) -> dict:
    default = config_dir / "log-sources.json"
    local = config_dir / "log-sources.local.json"
    cfg: dict = {}
    if default.exists():
        cfg = json.loads(default.read_text(encoding="utf-8"))
    if local.exists():
        local_cfg = json.loads(local.read_text(encoding="utf-8"))
        for src_id, src_cfg in local_cfg.get("sources", {}).items():
            cfg.setdefault("sources", {}).setdefault(src_id, {})
            cfg["sources"][src_id]["patterns"] = src_cfg.get("patterns", [])
    paths = cfg.get("paths", {})
    db_dir = paths.get("db_dir", "data/logs/db")
    cfg["paths"] = {
        "db_dir": str(base_dir / db_dir) if not Path(db_dir).is_absolute() else db_dir,
    }
    return cfg


def cmd_logs_ingest(args: argparse.Namespace) -> None:
    from .log_importer import SOURCE_DEFINITIONS, EXTRACTOR_VERSION, discover_files, file_fingerprint, parse_file
    from .log_db import (
        connect_state_db, connect_month_db, upsert_source, upsert_sessions,
        upsert_messages, upsert_actions, get_file_state, update_file_state,
        begin_run, finish_run, touched_month_keys,
    )
    from .log_util import stable_id, now_utc_iso, month_key_for_day_key

    base = Path(args.base_dir) if hasattr(args, "base_dir") and args.base_dir else Path.cwd()
    config_dir = Path(args.config_dir) if args.config_dir else base / "config"
    cfg = _load_log_sources_config(config_dir, base)
    db_dir = cfg["paths"]["db_dir"]

    state_conn = connect_state_db(db_dir)
    month_conns: dict = {}
    shared_state: dict = {}
    run_id = stable_id("run", now_utc_iso())
    begin_run(state_conn, run_id, "ingest")
    stats = {k: 0 for k in ("discovered_files", "processed_files", "skipped_files",
                              "sessions_upserted", "messages_upserted", "actions_upserted")}
    touched_months: set[str] = set()
    touched_days: set[str] = set()

    try:
        for source_id, definition in SOURCE_DEFINITIONS.items():
            patterns = cfg.get("sources", {}).get(source_id, {}).get("patterns", [])
            if not patterns:
                continue
            files = discover_files(patterns)
            if not files:
                continue
            upsert_source(state_conn, source_id=source_id, display_name=definition.display_name,
                          source_type=definition.source_type, root_path=";".join(patterns),
                          extractor_version=EXTRACTOR_VERSION)
            for file_path in files:
                stats["discovered_files"] += 1
                fp = file_fingerprint(file_path)
                file_state = get_file_state(state_conn, source_id, str(file_path))
                force_reparse = source_id == "codex_desktop_bridge" and shared_state.get("force_codex_bridge")
                if file_state and file_state["fingerprint"] == fp and not force_reparse:
                    stats["skipped_files"] += 1
                    continue
                parsed = parse_file(source_id, file_path, cfg, shared_state)
                fallback_ts = None
                if parsed["sessions"]:
                    fallback_ts = parsed["sessions"][0].get("started_at") or parsed["sessions"][0].get("ended_at")
                months = touched_month_keys(parsed["messages"], parsed["actions"], fallback_ts=fallback_ts)
                msg_by_month: dict = {}
                act_by_month: dict = {}
                for rec in parsed["messages"]:
                    mk = month_key_for_day_key(rec.get("day_key")) or ""
                    msg_by_month.setdefault(mk, []).append(rec)
                for rec in parsed["actions"]:
                    mk = month_key_for_day_key(rec.get("day_key")) or ""
                    act_by_month.setdefault(mk, []).append(rec)
                for mk in months:
                    if mk not in month_conns:
                        month_conns[mk] = connect_month_db(db_dir, mk)
                    conn = month_conns[mk]
                    if parsed["sessions"]:
                        upsert_sessions(conn, parsed["sessions"])
                    if msg_by_month.get(mk):
                        upsert_messages(conn, msg_by_month[mk])
                    if act_by_month.get(mk):
                        upsert_actions(conn, act_by_month[mk])
                    touched_months.add(mk)
                update_file_state(state_conn, source_id=source_id, path=str(file_path),
                                  size=file_path.stat().st_size, mtime_ns=file_path.stat().st_mtime_ns,
                                  fingerprint=fp, run_id=run_id, status="ok")
                stats["processed_files"] += 1
                stats["sessions_upserted"] += len(parsed["sessions"])
                stats["messages_upserted"] += len(parsed["messages"])
                stats["actions_upserted"] += len(parsed["actions"])
                if source_id == "codex_desktop_live_log":
                    shared_state["force_codex_bridge"] = True
                elif source_id == "codex_desktop_bridge":
                    shared_state["force_codex_bridge"] = False
                for rec in parsed["messages"]:
                    if rec.get("day_key"):
                        touched_days.add(rec["day_key"])
                for rec in parsed["actions"]:
                    if rec.get("day_key"):
                        touched_days.add(rec["day_key"])
        finish_run(state_conn, run_id, status="completed", message="ingest completed", stats=stats)
        state_conn.commit()
        for conn in month_conns.values():
            conn.commit()
    except Exception:
        for conn in month_conns.values():
            conn.rollback()
        raise
    finally:
        state_conn.close()
        for conn in month_conns.values():
            conn.close()

    print(f"DB: {db_dir}")
    print(f"Touched months: {', '.join(sorted(touched_months)) or '(none)'}")
    print(f"Touched days:   {', '.join(sorted(touched_days)) or '(none)'}")
    print(
        "Processed {processed_files} files, skipped {skipped_files}, "
        "sessions {sessions_upserted}, messages {messages_upserted}, actions {actions_upserted}".format(**stats)
    )


# ── argument parser ─────────────────────────────────────────────────────────

def _common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--period", "--week", required=True, metavar="PERIOD_KEY",
                   help="Period key, e.g. 2026-W15, 2026-04, 2026-04-07")
    p.add_argument("--config-dir", default=None,
                   help="Config directory (default: ./config)")
    p.add_argument("--reports-dir", default=None,
                   help="Reports output directory (default: ./reports/weekly)")
    p.add_argument("--base-dir", default=None,
                   help="Base directory for relative paths (default: cwd)")


def main() -> None:
    # FIX-4: force UTF-8 stdout on Windows (cp932 console garbles Japanese)
    import sys as _sys, io as _io
    if hasattr(_sys.stdout, "buffer"):
        _sys.stdout = _io.TextIOWrapper(_sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(_sys.stderr, "buffer"):
        _sys.stderr = _io.TextIOWrapper(_sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="python -m ai_shuho",
        description="AI-Shuho: weekly AI activity report generator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Aggregate SQLite logs → weekly-materials.json")
    _common_args(p_ingest)
    p_ingest.add_argument("--db-dir", default=None,
                          help="SQLite DB directory (default: from log-sources config)")
    p_ingest.set_defaults(func=cmd_ingest)

    # split-for-x
    p_split = sub.add_parser("split-for-x", help="Split draft.md → posts-draft.json")
    _common_args(p_split)
    p_split.set_defaults(func=cmd_split_for_x)

    # validate
    p_val = sub.add_parser("validate", help="Validate draft + posts")
    _common_args(p_val)
    p_val.set_defaults(func=cmd_validate)

    # publish
    p_pub = sub.add_parser("publish", help="Copy drafts to final output files")
    _common_args(p_pub)
    p_pub.add_argument("--publish-dir", default=None,
                       help="Output directory for final files (default: same as --reports-dir)")
    p_pub.set_defaults(func=cmd_publish)

    # list-periods
    p_lp = sub.add_parser("list-periods", help="List available periods (weeks) in SQLite DB")
    p_lp.add_argument("--config-dir", default=None, help="Config directory (default: ./config)")
    p_lp.add_argument("--base-dir", default=None, help="Base directory (default: cwd)")
    p_lp.set_defaults(func=cmd_list_periods)

    # logs-ingest
    p_li = sub.add_parser("logs-ingest", help="Ingest raw AI logs → SQLite DB")
    p_li.add_argument("--config-dir", default=None, help="Config directory (default: ./config)")
    p_li.add_argument("--base-dir", default=None, help="Base directory (default: cwd)")
    p_li.set_defaults(func=cmd_logs_ingest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
