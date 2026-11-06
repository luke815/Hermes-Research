"""Sweep daemon. One measure per pass, forever, train period only.

Scores the next unscored measure of the S3 slice, appends its rows to
results/sweeps/<today>.csv, and rewrites results/sweeps/leaderboard.json from
the rows on disk. A cell id already saved is skipped, so a restart continues
rather than starting over. Nothing here reads a bar after the train end,
reads validation or test, or touches the live score or the dashboard.

Run tracked:
    python3 scripts/sweep_daemon.py
The hourly health job restarts it when ops/sweep_heartbeat is missing or
older than 90 minutes, and does not start a second copy.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.indicators import LIBRARY_VERSION, META  # noqa: E402
from regime_tester.sweep import prepare, score_measure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "sweeps"
HEARTBEAT = ROOT / "ops" / "sweep_heartbeat"
PROGRESS = ROOT / "ops" / "sweep_progress.json"
SPACE = OUT_DIR / "space.json"
BOARD = OUT_DIR / "leaderboard.json"
PAUSE = 5
TOP_PER_FAMILY = 50


def stamp(line):
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEARTBEAT.with_suffix(".tmp")
    tmp.write_text(line + "\n")
    os.replace(tmp, HEARTBEAT)


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def out_path():
    return OUT_DIR / f"{today()}.csv"


def saved_ids():
    """Every cell id scored so far, across every day's file."""
    ids = set()
    for path in sorted(OUT_DIR.glob("*.csv")):
        ids.update(pd.read_csv(path, usecols=["id"])["id"])
    return ids


def append_rows(rows):
    """Append, then read back and refuse the write if it created a duplicate.

    A new day's file is created with the header before the first row lands, so a
    date rollover never reads a file that does not exist.
    """
    path = out_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        pd.DataFrame(columns=list(rows[0].keys())).to_csv(path, index=False)
    batch = pd.concat([pd.read_csv(path), pd.DataFrame(rows)], ignore_index=True)
    if batch["id"].duplicated().any():
        raise RuntimeError("append would write a duplicate cell id")
    tmp = path.with_suffix(".csv.tmp")
    batch.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return len(batch)


def family_of(measure):
    """Family from the library. A crossover pair is trend, as S2 counted it."""
    return META[measure][0] if measure in META else "trend"


def as_bool(series):
    return series.astype(str).str.lower().isin(["true", "1"])


def deflated(n):
    import math
    return round(2 + 0.5 * math.log10(max(int(n), 1)), 4)


def rewrite_leaderboard():
    """S4's ranking, recomputed from the newest sweep file on disk.

    A cell whose train firing rate, scaled by the validation window, expects
    fewer than 30 independent observations is marked insufficient here, before
    it is ever queued for a confirmation run.
    """
    files = sorted(OUT_DIR.glob("*.csv"))
    if not files:
        return 0
    path = files[-1]
    frame = pd.read_csv(path)
    space = json.loads(SPACE.read_text()) if SPACE.exists() else {}
    frame["family"] = frame["measure"].map(family_of)
    fragile = as_bool(frame["fragile"])
    duplicate = as_bool(frame["duplicate"])
    degenerate = as_bool(frame["degenerate"])
    below = as_bool(frame["below_minimum"])
    finite_t = frame["t_newey_west"].apply(lambda v: v == v and abs(v) != float("inf"))
    eligible = ~fragile & ~duplicate & ~degenerate & ~below & finite_t

    leaderboard = []
    by_family = []
    grouped = frame.sort_values("family").groupby("family", sort=True)
    for family, group in grouped:
        keep = group[eligible.loc[group.index]].copy()
        keep["abs_t"] = keep["t_newey_west"].abs()
        # Validation runs 549 days. A cell that fired n times over the train
        # window is expected to fire n * 549 / train_days times there, and one
        # below 30 is insufficient before it is queued.
        train_days = 1643
        keep["expected_validation_n"] = (keep["n_independent"] * 549 / train_days).round(1)
        keep["status"] = keep["expected_validation_n"].map(
            lambda n: "insufficient" if n < 30 else "unconfirmed")
        keep = keep.sort_values(["abs_t", "id"], ascending=[False, True]).head(TOP_PER_FAMILY)
        rows = []
        for _, row in keep.iterrows():
            rows.append({
                "cell_id": row["id"], "family": family,
                "target_family": row["target"],
                "rule": (f"{row['measure']} {row['transform']} {row['direction']} "
                         f"{int(row['threshold'])}"),
                "target": row["target"], "universe": row["universe"],
                "train_score": round(float(row["t_newey_west"]), 4),
                "train_spread_pct": round(float(row["spread_independent"]) * 100, 4),
                "train_n": int(row["n_independent"]),
                "expected_validation_n": float(row["expected_validation_n"]),
                "status": row["status"],
            })
        by_family.append({"family": family, "tested": int(len(group)),
                          "survivors": len(rows), "threshold_now": deflated(len(group))})
        leaderboard.extend(rows)

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
        "library_version": LIBRARY_VERSION,
        "train_period_hash": str(frame["train_period_hash"].iloc[0]),
        "cells_enumerated": int(space.get("cells", 0)),
        "cells_tested": int(len(frame)),
        "cells_skipped": int(space.get("skipped", 0)),
        "fragile": int(fragile.sum()),
        "duplicates": int(duplicate.sum()),
        "eligible": int(eligible.sum()),
        "by_family": by_family,
        "leaderboard": leaderboard,
    }
    tmp = BOARD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, BOARD)
    return len(leaderboard)


def next_measure(computed, done):
    """The first measure, alphabetically, that still has an unscored cell."""
    measures = sorted({c for f in computed.values() for c in f.columns})
    scored = {cid.split("|", 1)[0] for cid in done}
    for measure in measures:
        if measure not in scored:
            return measure, len(measures)
    return None, len(measures)


def pass_once(state):
    """Score one measure and rewrite the leaderboard. Returns the summary."""
    frames, computed, admitted, years, period_hash = state
    done = saved_ids()
    measure, total = next_measure(computed, done)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if measure is None:
        listed = rewrite_leaderboard()
        stamp(f"{now} idle measures={total} rows={len(done)} listed={listed}")
        return {"measure": None, "rows_appended": 0, "rows_total": len(done), "listed": listed}
    rows = score_measure(measure, frames, computed, admitted, years, period_hash, done)
    written = append_rows(rows) if rows else len(done)
    listed = rewrite_leaderboard()
    done_after = saved_ids()
    if len(done_after) != len(done | {r["id"] for r in rows}):
        raise RuntimeError("row count does not match the ids saved")
    record = {"as_of": now, "measure": measure, "rows_appended": len(rows),
              "rows_total": written, "measures_total": total, "listed": listed,
              "library_version": LIBRARY_VERSION}
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(record, indent=2) + "\n")
    stamp(f"{now} measure={measure} appended={len(rows)} rows={written} listed={listed}")
    print(json.dumps(record), flush=True)
    return record


def self_check(state):
    """Score one already-scored measure with its rows hidden, and check the result.

    Reads the newest sweep file that exists, so a date rollover does not make the
    check fail on a file that has not been created yet.
    """
    frames, computed, admitted, years, period_hash = state
    files = sorted(OUT_DIR.glob("*.csv"))
    if not files:
        return {"measure": None, "rows": 0, "matched": False, "note": "no sweep file yet"}
    saved = pd.read_csv(files[-1])
    measure = sorted(saved["measure"].unique())[0]
    fresh = score_measure(measure, frames, computed, admitted, years, period_hash, set())
    got = pd.DataFrame(fresh).sort_values("id").reset_index(drop=True)
    had = saved[saved["measure"] == measure].sort_values("id").reset_index(drop=True)
    if list(got["id"]) != list(had["id"]):
        raise RuntimeError(f"self-check id mismatch on {measure}")
    for col in ("spread_independent", "t_newey_west", "n_independent"):
        if not (got[col] - had[col]).abs().max() < 1e-9:
            raise RuntimeError(f"self-check {col} differs on {measure}")
    scratch = ROOT / "ops" / "sweep_selfcheck.csv"
    got.to_csv(scratch, index=False)
    read_back = pd.read_csv(scratch)
    scratch.unlink()
    if read_back["id"].duplicated().any() or len(read_back) != len(got):
        raise RuntimeError("self-check write did not round-trip")
    return {"measure": measure, "rows": len(got), "matched": True}


def main():
    state = prepare()
    checked = False
    while True:
        began = time.time()
        try:
            if not checked:
                result = self_check(state)
                checked = True
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                PROGRESS.parent.mkdir(parents=True, exist_ok=True)
                PROGRESS.write_text(json.dumps({"as_of": now, "self_check": result}, indent=2) + "\n")
                print(json.dumps({"self_check": result}), flush=True)
            record = pass_once(state)
        except Exception as exc:  # noqa: BLE001
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            stamp(f"{now} error={exc}")
            print(f"pass error: {exc}", flush=True)
            record = {"measure": "error"}
        # Idle once every measure is scored. The heartbeat still moves, so the
        # health job does not restart a finished sweep.
        time.sleep(3600 if record.get("measure") is None else max(0, PAUSE - (time.time() - began)))


if __name__ == "__main__":
    main()
