#!/usr/bin/env python3
"""Count rows and date span of compact item JSON files. Prints counts only."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAW = Path("/opt/data/workspace/regime-tester/data/raw")
DAY = 86_400_000
START = 1761004800000  # 2025-10-21
END = 1792972800000    # 2026-10-26


def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def main():
    stems = sys.argv[1:]
    for stem in stems:
        path = RAW / f"{stem}.json"
        items = json.loads(path.read_text())
        dates = sorted(it["date"] for it in items)
        missing = []
        if dates:
            have = set(dates)
            t = dates[0]
            while t <= dates[-1]:
                if t not in have:
                    missing.append(day(t))
                t += DAY
        print(
            json.dumps(
                {
                    "stem": stem,
                    "rows": len(items),
                    "first": day(dates[0]) if dates else None,
                    "last": day(dates[-1]) if dates else None,
                    "span_days": ((dates[-1] - dates[0]) // DAY + 1) if dates else 0,
                    "dupes": len(dates) - len(set(dates)),
                    "missing": missing,
                    "covers_window": bool(dates) and dates[0] <= START and dates[-1] >= END,
                }
            )
        )


if __name__ == "__main__":
    main()
