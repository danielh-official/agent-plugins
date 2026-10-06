#!/usr/bin/env python3
"""Vectors copied from DailyCaloriesTests/DailyCaloriesTests.swift. Run: python3 selfcheck.py"""
from calslashd import compute, next_goal

NOW = "2026-01-11T00:00:00+00:00"  # start 2026-01-01 midnight UTC + 10 days


def run(**kw):
    base = dict(tz="UTC", start_date="2026-01-01", now=NOW, limit=2000, total=0)
    return compute({**base, **kw})


def saved(surplus, limit=2000):
    return run(limit=limit, total=10 * limit - surplus)


# timeLeftIsSurplusDividedByLimit: 10d @2000, 10000 eaten -> 5 days
assert abs(run(total=10_000)["time_left_seconds"] - 5 * 86_400) < 1
# timeLeftIsZeroInDeficit
assert run(total=99_000)["time_left_seconds"] == 0
# skippedFullDaysShortenElapsedDaysAndSurplus
r = run(total=12_000, skipped_full_days=2)
assert abs(r["elapsed_days"] - 8) < 1e-3 and abs(r["daily_average"] - 1500) < 1e-3
assert abs(r["surplus"] - (8 * 2000 - 12_000)) < 1e-3
# skippedDaysPushGoalArrivalLater (+2 days)
from datetime import datetime
a = datetime.fromisoformat(run(total=12_000, goal=1000)["goal_eta"])
b = datetime.fromisoformat(run(total=12_000, goal=1000, skipped_full_days=2)["goal_eta"])
assert abs((b - a).total_seconds() - 2 * 86_400) < 1e-3
# skippedTodayPausesAccrualForTheElapsedPartOfToday: half a day elapsed
n = "2026-01-11T12:00:00+00:00"
d = run(total=12_000, now=n)["elapsed_days"] - run(total=12_000, now=n, today_skipped=True)["elapsed_days"]
assert abs(d - 0.5) < 1e-3
# ladder
assert saved(700)["next_goal"] == 750
assert saved(2500)["next_goal"] == 4000
assert saved(1800, 1850)["next_goal"] == 1850
assert saved(-500)["next_goal"] == 0
assert run(total=20_000 + 500)["upcoming_goals"][:3] == [0, 250, 500]
g = saved(700)["upcoming_goals"][:12]
assert all(x < y for x, y in zip(g, g[1:]))
assert abs(saved(5000)["days_saved"] - 2.5) < 1e-4
# goalMetFlipsAtExactlyTheTargetSurplus
assert saved(4000) and run(total=16_000, goal_days=2)["goal_met"]
assert not run(total=16_001, goal_days=2)["goal_met"]
assert next_goal(5, 0) == 0
# DST: NY clocks fall back 2026-11-01, so local midnight->midnight spans 73h, not 72h.
r = compute(dict(tz="America/New_York", start_date="2026-10-30", now="2026-11-02T00:00:00-05:00",
                 limit=2000, total=0))
assert abs(r["elapsed_days"] - 73 / 24) < 1e-9, r["elapsed_days"]
print("ok")
