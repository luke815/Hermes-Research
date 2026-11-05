"""S3 train-only scorer.

One row per cell, train period only, appended to
results/sweeps/<date>.csv as each measure finishes. A rerun skips cell ids
already saved. This script never reads a bar after 2024-06-30 and never
admits a factor. The scoring rules live in regime_tester/sweep.py so the
daemon scores the same cells.

The pre-registered slice is the testable daily cells at conditioning none.
Event targets, intraday timeframes and the point-in-time universe are
skipped by the enumerator and are not scored here.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.sweep import prepare, score_measure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "sweeps"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
OUT = OUT_DIR / f"{TODAY}.csv"


def main():
    started = time.time()
    frames, computed, admitted, years, period_hash = prepare()

    done = set()
    if OUT.exists():
        done = set(pd.read_csv(OUT, usecols=["id"])["id"])

    measures = sorted({c for f in computed.values() for c in f.columns})
    rows_written = 0
    for measure in measures:
        rows = score_measure(measure, frames, computed, admitted, years, period_hash, done)
        if rows:
            batch = pd.DataFrame(rows)
            if OUT.exists():
                batch = pd.concat([pd.read_csv(OUT), batch], ignore_index=True)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            batch.to_csv(OUT, index=False)
            done.update(r["id"] for r in rows)
            rows_written += len(rows)
        print(json.dumps({"measure": measure, "rows": rows_written,
                          "elapsed_s": round(time.time() - started, 1)}), flush=True)
    print(json.dumps({"done": rows_written, "elapsed_s": round(time.time() - started, 1)}))


if __name__ == "__main__":
    main()
