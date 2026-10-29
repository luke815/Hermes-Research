#!/usr/bin/env python3
"""Merge spilled Laevitas envelopes into one items JSON, sorted by date, deduped."""
import json
import sys
from pathlib import Path

RAW = Path("/opt/data/workspace/regime-tester/data/raw")


def unwrap(obj):
    if isinstance(obj, str):
        obj = json.loads(obj)
    if isinstance(obj, dict) and isinstance(obj.get("result"), str):
        obj = json.loads(obj["result"])
    return obj


def main():
    stem = sys.argv[1]
    sources = sys.argv[2:]
    by_date = {}
    for src in sources:
        obj = unwrap(json.loads(Path(src).read_text()))
        rows = obj if isinstance(obj, list) else obj["items"]
        for item in rows:
            by_date[item["date"]] = item
    items = [by_date[k] for k in sorted(by_date)]
    dest = RAW / f"{stem}.json"
    dest.write_text(json.dumps(items, separators=(",", ":")))
    print(
        json.dumps(
            {
                "stem": stem,
                "rows": len(items),
                "first": items[0]["date"] if items else None,
                "last": items[-1]["date"] if items else None,
                "bytes": dest.stat().st_size,
                "sources": len(sources),
            }
        )
    )


if __name__ == "__main__":
    main()
