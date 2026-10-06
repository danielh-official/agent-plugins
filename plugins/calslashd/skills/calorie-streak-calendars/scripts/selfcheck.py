#!/usr/bin/env python3
"""Run: python3 selfcheck.py"""

from streak import build

base = {"tz": "UTC", "limit": 2000, "now": "2026-11-03T12:00:00+00:00"}
days = {
    "2026-10-30": {"dietary": 1900},
    "2026-10-31": {"dietary": 1800},
    "2026-11-01": {"dietary": 2500},  # over: breaks
    "2026-11-02": {"dietary": 1500},
    "2026-11-03": {"dietary": 500},  # today, open
}
out = build({**base, "start_date": "2026-10-30", "days": days})
assert "October 2026" in out and "November 2026" in out
assert "Current streak: 1  Best streak: 2  Days under: 3 of 4 tracked" in out, out
# skipped day is neutral; missing day breaks
out = build(
    {**base, "start_date": "2026-10-30", "days": days, "skipped_dates": ["2026-11-01"]}
)
assert "Current streak: 3  Best streak: 3" in out, out
del days["2026-11-02"]
out = build({**base, "start_date": "2026-10-30", "days": days})
assert "Current streak: 0" in out, out
# eat_back nets active energy
out = build(
    {
        **base,
        "start_date": "2026-11-01",
        "eat_back": True,
        "days": {"2026-11-01": {"dietary": 2500, "active": 600}},
    }
)
assert "Days under: 1 of 1" in out, out
print("ok")
