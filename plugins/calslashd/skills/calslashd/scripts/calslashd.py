#!/usr/bin/env python3
"""CalSlashD budget math: a port of DailyCalories/Misc/CalorieBudget.swift.

Usage: python3 calslashd.py '<json>'   (or JSON on stdin)
Input keys: tz, start_date (YYYY-MM-DD), limit, total, burned, eat_back, skipped_dietary,
            skipped_active, skipped_full_days, today_skipped, goal_days, goal (optional kcal target),
            now (ISO-8601 with offset; default: current time).
total/burned are raw Health sums since the start date; skipped_* are Health sums over the
skipped dates (today included), which this script nets out like the app's realBudget.
Output: JSON of the stats the app shows. Energy is kcal throughout.
"""

import json
import math
import sys
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DAY = 86_400.0
STEP = 250.0
UTC = timezone.utc


def _secs(a, b):
    # Aware datetimes sharing one zoneinfo subtract by wall clock (DST-blind). Go via UTC,
    # like Swift's timeIntervalSince.
    return (a.astimezone(UTC) - b.astimezone(UTC)).total_seconds()


def _midnight(d, tz):
    return datetime.combine(d, time.min, tzinfo=tz)


def next_goal(s, limit):
    if limit <= 0 or s < 0:
        return 0.0
    if s < limit:  # clamp: a non-multiple-of-250 limit must not overshoot the day rung
        return min((math.floor(s / STEP) + 1) * STEP, float(limit))
    return (math.floor(s / limit) + 1) * float(limit)


def hms(seconds):
    m = int(seconds // 60)
    d, m = divmod(m, 1440)
    h, m = divmod(m, 60)
    return f"{d}d {h}h {m}m"


def compute(i):
    tz = ZoneInfo(i["tz"])
    limit = float(i["limit"])
    if limit <= 0:
        raise ValueError("limit must be > 0")
    now = datetime.fromisoformat(i["now"]) if i.get("now") else datetime.now(UTC)
    now = now.astimezone(tz)
    start = _midnight(date.fromisoformat(i["start_date"]), tz)
    # Skipped days: their calories leave the totals (burned only counts with eat-back on).
    total = float(i["total"]) - float(i.get("skipped_dietary", 0))
    burned = (
        float(i.get("burned", 0)) - float(i.get("skipped_active", 0))
        if i.get("eat_back")
        else 0.0
    )
    skipped_full = float(i.get("skipped_full_days", 0))
    today_skipped = bool(i.get("today_skipped", False))
    goal_days = float(i.get("goal_days", 1))

    day_fraction = min(max(_secs(now, _midnight(now.date(), tz)) / DAY, 0), 1)
    skipped = skipped_full + (
        _secs(now, _midnight(now.date(), tz)) / DAY if today_skipped else 0
    )
    raw_days = _secs(now, start) / DAY - skipped
    net = total - burned
    surplus = max(raw_days, 0) * limit - net
    time_left = max(0.0, surplus) / limit * DAY

    def goal_eta(g):
        days = (g + net) / limit + skipped_full + (1 if today_skipped else 0)
        return (
            (start.astimezone(UTC) + timedelta(seconds=days * DAY))
            .astimezone(tz)
            .isoformat()
        )

    goals, s = [], surplus
    for _ in range(16):
        s = next_goal(s, limit)
        goals.append(s)
    base = (math.floor(surplus / STEP) + 1) * STEP

    return {
        "net_calories": net,
        "elapsed_days": max(raw_days, 1),
        "daily_average": net / max(raw_days, 1),
        "surplus": surplus,
        "time_left_seconds": time_left,
        "time_left": hms(time_left),
        "days_saved": time_left / DAY,
        "goal_surplus": goal_days * limit,
        "goal_met": surplus >= goal_days * limit,
        "next_goal": goals[0],
        "next_goal_eta": goal_eta(goals[0]),
        **(
            {"goal_eta": goal_eta(float(i["goal"]))} if "goal" in i else {}
        ),  # ETA for any surplus target
        "upcoming_goals": goals,
        "upcoming_steps": [base + k * STEP for k in range(20)],
        "day_fraction": day_fraction,
        "expected_by_now": limit * day_fraction,
    }


if __name__ == "__main__":
    try:
        raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
        print(json.dumps(compute(json.loads(raw)), indent=2))
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        sys.exit(f"calslashd: bad input ({type(e).__name__}: {e})")
