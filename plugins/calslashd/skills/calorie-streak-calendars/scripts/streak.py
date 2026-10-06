#!/usr/bin/env python3
"""Streak calendar: one grid per month from the start date's month through the current month.

Usage: python3 streak.py '<json>'   (or JSON on stdin)
Input keys: tz, start_date (YYYY-MM-DD), limit (kcal/day), eat_back (bool),
            days ({"YYYY-MM-DD": {"dietary": kcal, "active": kcal}}, local-day Health sums),
            skipped_dates (optional list), now (optional ISO-8601 with offset).
A day is under when dietary (minus active if eat_back) <= limit. Days with no food logged are
no-data and break the streak; skipped dates are neutral; today is never counted (still open).
Output: plain text, a calendar per month plus a summary.
"""

import calendar
import json
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UNDER, OVER, NODATA, SKIP, TODAY = "✅", "❌", "⬜", "➖", "⏳"
BLANK = "  "


def build(i):
    tz = ZoneInfo(i["tz"])
    limit = float(i["limit"])
    now = (
        datetime.fromisoformat(i["now"]) if i.get("now") else datetime.now(timezone.utc)
    )
    today = now.astimezone(tz).date()
    start = date.fromisoformat(i["start_date"])
    skipped = {date.fromisoformat(d) for d in i.get("skipped_dates", [])}
    days = i.get("days", {})

    marks, run, best, under_n, tracked = {}, 0, 0, 0, 0
    d = start
    while d <= today:
        entry = days.get(d.isoformat(), {})
        dietary = float(entry.get("dietary", 0))
        net = dietary - (float(entry.get("active", 0)) if i.get("eat_back") else 0)
        if d in skipped:
            mark = SKIP
        elif dietary <= 0:
            mark = NODATA
        elif net <= limit:
            mark = TODAY if d == today else UNDER
        else:
            mark = OVER
        marks[d] = mark
        if mark == UNDER:
            run, under_n = run + 1, under_n + 1
            best = max(best, run)
        elif mark in (OVER, NODATA):
            run = 0
        if mark in (UNDER, OVER):
            tracked += 1
        d += timedelta(days=1)

    out = []
    y, m = start.year, start.month
    while (y, m) <= (today.year, today.month):
        out.append(f"{calendar.month_name[m]} {y}\nMo Tu We Th Fr Sa Su")
        for week in calendar.monthcalendar(y, m):
            row = " ".join(
                marks.get(date(y, m, n), BLANK) if n else BLANK for n in week
            )
            if row.strip():  # skip weeks entirely before the start or after today
                out.append(row.rstrip())
        out.append("")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    out.append(
        f"{UNDER} under {int(limit)} kcal  {OVER} over  {NODATA} no data  "
        f"{SKIP} skipped  {TODAY} today (still open)"
    )
    out.append(
        f"Current streak: {run}  Best streak: {best}  Days under: {under_n} of {tracked} tracked"
    )
    return "\n".join(out)


if __name__ == "__main__":
    try:
        raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
        print(build(json.loads(raw)))
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        sys.exit(f"streak: bad input ({type(e).__name__}: {e})")
