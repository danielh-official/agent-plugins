#!/usr/bin/env python3
"""Check the rules specific to this plugin; the marketplace root checks the rest."""

import sys
from pathlib import Path


def validate(root):
    errors = []
    if len(list((root / "skills").glob("*/SKILL.md"))) != 1:
        errors.append("Expected exactly one skills/*/SKILL.md")
    return errors


def main():
    if len(sys.argv) > 2:
        print("Usage: python3 scripts/validate.py [plugin-root]", file=sys.stderr)
        return 2
    root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) == 2
        else Path(__file__).resolve().parent.parent
    )
    errors = validate(root)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: plugin-specific checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
