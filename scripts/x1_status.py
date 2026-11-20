"""Where X1 stands, read from the sweep status line, the work list and the panel.

The clause needs the status line to show the panel's name count and cells per
hour above 5,000 for one full hour. This script reads that line, counts the
emittable cells still open on the current universe, and checks whether the
panel the sweep reads carries high and low. It does not score and does not pull.
"""

import csv
import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFORMS = {"raw", "pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30",
              "persistence", "acceleration", "divergence_20", "xs_rank", "ratio_btc"}
MARKET = {"basis_pct_252", "basis_venue", "funding_dispersion_oiw", "funding_oiw",
          "funding_oiw_avg_7", "funding_persist_high_oiw", "funding_persist_low_oiw",
          "rv_30", "rv_7", "rv_ratio_7_30", "vol_of_vol_30"}


def _emittable(cell_id):
    parts = cell_id.split("|")
    return (len(parts) >= 8 and parts[1] in TRANSFORMS
            and parts[6] == "none" and parts[7] == "daily")


def _with_range(directory, limit):
    files = [name for name in os.listdir(directory) if name.endswith(".csv")]
    found = 0
    for name in sorted(files)[:limit]:
        header = open(os.path.join(directory, name)).readline().split(",")
        if "high" in header and "low" in header:
            found += 1
    return {"files": len(files), "checked": min(limit, len(files)), "with_high_low": found}


def main():
    line = open(os.path.join(ROOT, "ops", "sweep_status")).read().strip()
    heartbeat = json.load(open(os.path.join(ROOT, "ops", "sweep_xs_heartbeat")))
    panel = os.path.join(ROOT, "data", "panel_xs_laevitas")
    work = json.load(open(os.path.join(ROOT, "results", "sweeps", "cross_section_cells.json")))
    scored = set()
    sweeps = os.path.join(ROOT, "results", "sweeps")
    for name in os.listdir(sweeps):
        if not name.endswith("_xs_vec.csv"):
            continue
        with open(os.path.join(sweeps, name)) as handle:
            for row in csv.DictReader(handle):
                if row.get("names") == "234":
                    scored.add(row["id"])
    open_ids = [cell for cell in work if _emittable(cell) and cell not in scored]
    market = sum(1 for cell in open_ids if cell.split("|", 1)[0] in MARKET)
    out = {
        "item": "X1",
        "status_line": line,
        "panel_files": len([n for n in os.listdir(panel) if n.endswith(".csv")]),
        "sweep": {"pid": heartbeat.get("pid"), "version": heartbeat.get("version"),
                  "phase": heartbeat.get("phase"), "cycles": heartbeat.get("cycles"),
                  "names": heartbeat.get("names"), "remaining": heartbeat.get("remaining"),
                  "ts": heartbeat.get("ts")},
        "cells_per_hour_above_5000": "cells per hour" in line and _rate(line) > 5000,
        "work_list": len(work),
        "scored_on_234": len(scored),
        "open_emittable": len(open_ids),
        "open_market_level": market,
        "open_needs_range": len(open_ids) - market,
        "laevitas_range": _with_range(panel, 400),
        "old_panel_range": _with_range(os.path.join(ROOT, "data", "panel_xs"), 10000),
    }
    path = write_result("x1_status", out, inputs=[
        "ops/sweep_status", "ops/sweep_xs_heartbeat",
        "results/sweeps/cross_section_cells.json",
        "data/panel_xs_laevitas", "data/panel_xs"])
    print(json.dumps(out, indent=1))
    print(path)


def _rate(line):
    try:
        return int(line.split("cells per hour", 1)[1].split(",")[0].strip())
    except (IndexError, ValueError):
        return 0


if __name__ == "__main__":
    main()
