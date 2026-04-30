"""
Period calculation: week / day / month / custom.
All datetime math is done in local time with no external deps.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta

WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _effective_date(dt: datetime, sys_config: dict) -> date:
    """Shift datetime back by period_start_hour so the cutoff hour belongs to the previous period."""
    hour = int(sys_config.get("period_start_hour", 3))
    return (dt - timedelta(hours=hour)).date()


def _week_start(d: date, sys_config: dict) -> date:
    """Return the Monday (or configured weekday) that starts the week containing d."""
    target_wd = WEEKDAY_MAP.get(str(sys_config.get("period_start_weekday", "monday")).lower(), 0)
    delta = (d.weekday() - target_wd) % 7
    return d - timedelta(days=delta)


def period_start_for_date(d: date, sys_config: dict) -> date:
    unit = str(sys_config.get("period_unit", "week")).lower()
    if unit == "week":
        return _week_start(d, sys_config)
    if unit == "day":
        return d
    if unit == "month":
        return d.replace(day=1)
    # custom: period_days — start of the "custom" period is undefined without a base;
    # for key parsing we use the start date itself as the key.
    return d


def period_key_for_date(d: date, sys_config: dict) -> str:
    unit = str(sys_config.get("period_unit", "week")).lower()
    start = period_start_for_date(d, sys_config)
    if unit == "week":
        iso = start.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if unit == "month":
        return start.strftime("%Y-%m")
    # day or custom: use start date
    return start.strftime("%Y-%m-%d")


def period_key_from_datetime(dt: datetime, sys_config: dict) -> str:
    d = _effective_date(dt, sys_config)
    return period_key_for_date(d, sys_config)


def parse_period_key(period_key: str, sys_config: dict) -> tuple[date, date]:
    """Return (start_date, end_date) inclusive for the period_key."""
    unit = str(sys_config.get("period_unit", "week")).lower()

    if unit == "week" or (period_key.startswith("20") and "-W" in period_key):
        year_str, week_str = period_key.split("-W")
        year, week = int(year_str), int(week_str)
        target_wd = WEEKDAY_MAP.get(str(sys_config.get("period_start_weekday", "monday")).lower(), 0)
        # ISO week always starts Monday; shift if needed
        iso_start = date.fromisocalendar(year, week, 1)
        delta = (target_wd - 0) % 7  # offset from ISO Monday
        start = iso_start + timedelta(days=delta)
        # If the configured weekday is not Monday, the week key may straddle ISO weeks
        # Re-align: find the configured weekday on or before iso_start
        start = _week_start(iso_start, sys_config)
        end = start + timedelta(days=6)
        return start, end

    if unit == "month" or (len(period_key) == 7 and period_key[4] == "-"):
        year, month = int(period_key[:4]), int(period_key[5:7])
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return start, end

    # day or custom: YYYY-MM-DD
    start = date.fromisoformat(period_key)
    days = int(sys_config.get("period_days", 1)) if unit == "custom" else 1
    end = start + timedelta(days=days - 1)
    return start, end


def period_day_keys(period_key: str, sys_config: dict) -> list[str]:
    """Return all YYYY-MM-DD strings in the period."""
    start, end = parse_period_key(period_key, sys_config)
    keys = []
    d = start
    while d <= end:
        keys.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return keys


def format_period_display(period_key: str) -> str:
    """Convert period key to header display form: 2026-W15 → 2026/W15, 2026-04 → 2026/04, etc."""
    return period_key.replace("-W", "/W").replace("-", "/", 1) if "-W" not in period_key else period_key.replace("-W", "/W")


def period_label(period_key: str, sys_config: dict) -> str:
    """Human-readable label: '2026年 W15（4/7〜4/13）' etc."""
    start, end = parse_period_key(period_key, sys_config)
    unit = str(sys_config.get("period_unit", "week")).lower()
    if unit == "week":
        _, week, _ = start.isocalendar()
        return f"{start.year}年 W{week:02d}（{start.month}/{start.day}〜{end.month}/{end.day}）"
    if unit == "month":
        return f"{start.year}年{start.month}月"
    return f"{start.strftime('%Y-%m-%d')}〜{end.strftime('%Y-%m-%d')}"
