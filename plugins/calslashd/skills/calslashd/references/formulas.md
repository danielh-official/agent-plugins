# CalSlashD formulas

Ported from `DailyCalories/Misc/CalorieBudget.swift` and `Misc/DailyStatHelpers.swift` (`dayFraction`, `expectedByNow`). `scripts/calslashd.py` is the executable form; `scripts/selfcheck.py` holds vectors copied from `DailyCaloriesTests/DailyCaloriesTests.swift`.

## Conventions
- Energy in kcal. 250 kcal is the goal step (hard-coded in the app). Limit range in the app: 500–10000.
- Start day = local midnight (DST-safe). Elapsed time = absolute seconds / 86400, so a DST day counts 23 or 25 hours. Python: subtract via UTC, add via UTC (same-tz aware datetime math is wall-clock).
- Health reads: all sources, lower bound start-of-day, upper bound **end of today** (so evening-stamped meals count today).
- Skipped days: their calories are already excluded from `total`; only the clock changes.

## Known doc drift
`CLAUDE.md` says goals are `[0, 250 … 2000]`; code is unbounded (250-steps below one day, then whole-day rungs).

## Planned: BMR/TDEE (not built)
Would need age, sex, height, weight from Health, which the app never reads. Before shipping any such calculation, add to SKILL.md that output is not medical advice and users should consult a doctor.
