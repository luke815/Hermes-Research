"""Mark every pre-fix cross-sectional confirmation void.

A verdict that starts with "void" but carries a reason after it still reads as
rejected to anything matching the word exactly. The old text is kept in
void_before, and the verdict becomes the word void. A void cell can be scored
again, so the old verdict is recorded rather than closed.
"""

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(ROOT, "results", "sweeps", "confirmations.json")


def void_pre_fix(rows):
    """Set verdict to void on every cross-sectional row, keeping the old text."""
    changed = 0
    for row in rows:
        if "pit_cross_section" not in row.get("cell_id", ""):
            continue
        old = row.get("verdict")
        if old == "void":
            continue
        row["void_before"] = old
        row["verdict"] = "void"
        row["voided_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row["void_reason"] = "pre-fix scorer; the current method has not scored this cell"
        changed += 1
    return changed


def main():
    rows = json.loads(open(RECORD).read())
    changed = void_pre_fix(rows)
    tmp = RECORD + ".tmp"
    json.dump(rows, open(tmp, "w"), indent=2)
    os.replace(tmp, RECORD)
    xs = [row for row in rows if "pit_cross_section" in row.get("cell_id", "")]
    not_void = [row for row in xs if row.get("verdict") != "void"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {
        "task": "A2",
        "date": today,
        "written_by": "scripts/a2_void.py",
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confirmations": RECORD,
        "rows": len(rows),
        "cross_sectional_rows": len(xs),
        "cross_sectional_not_void": len(not_void),
        "voided_this_run": changed,
    }
    dest = os.path.join(ROOT, "results", f"{today}_a2_statistics.json")
    json.dump(out, open(dest, "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
