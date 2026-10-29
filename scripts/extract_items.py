#!/usr/bin/env python3
"""Extract items arrays from spilled Laevitas envelopes into data/raw/<stem>.json."""
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


def extract(src, stem):
    text = Path(src).read_text()
    obj = unwrap(json.loads(text))
    items = obj["items"]
    dest = RAW / f"{stem}.json"
    dest.write_text(json.dumps(items, separators=(",", ":")))
    dates = [it.get("date") for it in items if isinstance(it, dict) and "date" in it]
    meta = obj.get("meta") or {}
    print(
        json.dumps(
            {
                "stem": stem,
                "rows": len(items),
                "first": min(dates) if dates else None,
                "last": max(dates) if dates else None,
                "bytes": dest.stat().st_size,
                "pages": meta.get("total_pages"),
                "meta_items": meta.get("items"),
                "series": obj.get("series"),
            }
        )
    )


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2])
