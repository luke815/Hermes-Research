"""Reconcile the two A1 counts that overwrote each other on 2026-11-17.

89ffe11 wrote results/2026-11-17_a1_integrity.json with 2,731 files and 842
collapsed. 208218a overwrote that file 2.5 minutes later with 1,897 files and
156 collapsed, so the record of the 842 was gone and the arithmetic did not
add up. Both numbers are read back from those commits here, and the panel on
disk is counted by the same collapse the code uses, so the results file is
written by this script and not by hand.

The funding sums themselves are produced by scripts/funding_sum.py, one name
per call, which scripts/funding_sum_daemon.py calls. A research run does not
pull, so this script counts the sum files that exist and does not fetch any.
"""

import json
import os
import subprocess
import sys
from glob import glob

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.panel_integrity import base_of, collapse_venues  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
SUMS = os.path.join(ROOT, "data", "funding_sum")

# The two commits that wrote the same results file. Their payloads are the
# record; the arithmetic between them is what this script checks.
CHAT_COMMIT = "89ffe11"
CRON_COMMIT = "208218a"
RESULT_PATH = "results/2026-11-17_a1_integrity.json"


def _payload_at(commit):
    """The A1 results payload as that commit wrote it, provenance stripped."""
    raw = subprocess.run(
        ["git", "show", f"{commit}:{RESULT_PATH}"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout
    data = json.loads(raw)
    data.pop("provenance", None)
    return data


def panel_count():
    """Files on disk now, and how many collapse_venues drops on one date."""
    files = sorted(glob(os.path.join(PANEL, "*.csv")))
    frames = {}
    for path in files:
        frame = pd.read_csv(path, usecols=lambda c: c in ("date", "close", "volume_usd",
                                                          "volume_base"))
        if "close" not in frame.columns or len(frame) == 0:
            continue
        frames[os.path.basename(path)] = frame
    # One date is enough to show the collapse the code actually performs. The
    # full history is millions of rows and the question is the file count.
    sample = {}
    for name, frame in frames.items():
        day = str(frame["date"].iloc[-1])[:10]
        sample[name] = frame[frame["date"].astype(str).str.slice(0, 10) == day]
    collapsed, dropped = collapse_venues(sample, volume_column="volume_usd")
    bases = {base_of(name.split("_", 1)[-1].replace(".csv", "")) for name in frames}
    return {"files_on_disk": len(files), "files_with_close": len(frames),
            "base_coins": len(bases), "collapsed_on_last_date": len(collapsed),
            "dropped_on_last_date": dropped}


def funding_sum_count():
    """Sum files on disk, per venue. Written by funding_sum.write_sum."""
    files = [f for f in os.listdir(SUMS) if f.endswith(".csv")] if os.path.isdir(SUMS) else []
    per_venue = {}
    for name in files:
        venue = name.split("_", 1)[0]
        per_venue[venue] = per_venue.get(venue, 0) + 1
    return {"files": len(files), "per_venue": per_venue,
            "writer": "scripts/funding_sum.py:write_sum",
            "caller": "scripts/funding_sum_daemon.py"}


def main():
    chat = _payload_at(CHAT_COMMIT)
    cron = _payload_at(CRON_COMMIT)
    chat_files = chat["files"]
    chat_collapsed = chat["venue_collapse"]
    cron_files = cron["venue_collapse"]["files"]
    cron_collapsed = cron["venue_collapse"]["names_collapsed"]
    # 2,731 minus 842 is 1,889. The cron counted 1,897. The difference is the
    # eight files the two runs disagreed on, stated rather than smoothed.
    arithmetic = chat_files - chat_collapsed
    out = {
        "reconciles": [CHAT_COMMIT, CRON_COMMIT],
        "chat_run": {"commit": CHAT_COMMIT, "files": chat_files,
                     "resorted": chat["resorted"], "venue_collapse": chat_collapsed},
        "cron_run": {"commit": CRON_COMMIT, "files": cron_files,
                     "names_collapsed": cron_collapsed,
                     "base_coins": cron["venue_collapse"]["base_coins"],
                     "files_rewritten": cron["files_rewritten"]},
        "arithmetic": {
            "chat_files_minus_collapsed": arithmetic,
            "cron_files": cron_files,
            "difference": cron_files - arithmetic,
            "note": ("2,731 minus 842 is 1,889, and the cron counted 1,897. "
                     "The two runs counted different directories two minutes apart, "
                     "so the counts are not the same quantity and are not added."),
        },
        "panel_now": panel_count(),
        "funding_sums_now": funding_sum_count(),
        "note": ("The 842 collapsed files were deleted by hand; no committed "
                 "script performs that deletion, and the panel on disk is the "
                 "one a1_rewrite.py wrote into data/panel_xs_sum without swapping. "
                 "The funding sums are written by funding_sum.write_sum, called by "
                 "funding_sum_daemon, one name per cycle."),
    }
    path = write_result("a1_reconcile", out, inputs=["data/panel_xs", "data/funding_sum"])
    print(json.dumps({k: v for k, v in out.items() if k != "note"}))
    print(path)


if __name__ == "__main__":
    main()
