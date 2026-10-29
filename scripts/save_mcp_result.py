"""Save one Laevitas MCP result that spilled or was written to a path.

Usage: python3 save_mcp_result.py <spill_or_file> <outfile_stem>
Reads the tool envelope, extracts items, writes data/raw/<stem>.json as a list.
Prints a count only.
"""
import json
import sys
from pathlib import Path

RAW = Path("/opt/data/workspace/regime-tester/data/raw")


def items_from(obj):
    if isinstance(obj, str):
        obj = json.loads(obj)
    if isinstance(obj, dict) and "result" in obj and isinstance(obj["result"], str):
        obj = json.loads(obj["result"])
    if isinstance(obj, dict) and "items" in obj:
        return obj["items"]
    data = obj.get("data", obj) if isinstance(obj, dict) else obj
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    if isinstance(data, list):
        return data
    raise SystemExit(f"no items, type={type(obj).__name__} keys={list(obj)[:8] if isinstance(obj, dict) else ''}")


def main() -> None:
    src, stem = sys.argv[1], sys.argv[2]
    text = Path(src).read_text()
    rows = items_from(json.loads(text) if text.lstrip().startswith("{") else text)
    out = RAW / f"{stem}.json"
    out.write_text(json.dumps(rows))
    dates = [r.get("date") for r in rows if isinstance(r, dict)]
    print(f"saved {len(rows)} {stem} first={min(dates) if dates else None} last={max(dates) if dates else None}")


if __name__ == "__main__":
    main()
