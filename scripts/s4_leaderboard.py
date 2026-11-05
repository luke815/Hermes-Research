"""S4 leaderboard.

Ranks the train-only rows already written by the scorer. It reads
results/sweeps/2026-11-05.csv and results/sweeps/space.json, and nothing
dated after the train period. It does not recompute a return, it does not
read validation or test, and it does not admit a factor.
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.indicators import LIBRARY_VERSION, META  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCORED = ROOT / "results" / "sweeps" / "2026-11-05.csv"
SPACE = ROOT / "results" / "sweeps" / "space.json"
OUT = ROOT / "results" / "sweeps" / "leaderboard.json"
RESULTS = ROOT / "results" / "2026-11-05_s4_leaderboard.json"

TOP_PER_FAMILY = 50
MIN_INDEPENDENT = 40


def family_of(measure):
    """Family from the library. A crossover pair is trend, as S2 counted it."""
    if measure in META:
        return META[measure][0]
    return "trend"


def as_bool(series):
    return series.astype(str).str.lower().isin(["true", "1"])


def deflated(n):
    """The confirmation bar for a family, from the cells tested in it."""
    return round(2 + 0.5 * math.log10(max(int(n), 1)), 4)


def main():
    frame = pd.read_csv(SCORED)
    space = json.loads(SPACE.read_text())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if frame["id"].duplicated().any():
        raise SystemExit("duplicate cell id in the scored file")
    if frame["train_period_hash"].nunique() != 1:
        raise SystemExit("more than one train period hash")
    if set(frame["library_version"].astype(str)) != {LIBRARY_VERSION}:
        raise SystemExit("library version does not match")

    frame["family"] = frame["measure"].map(family_of)
    unknown = sorted(set(frame.loc[frame["family"].isna(), "measure"]))
    if unknown:
        raise SystemExit(f"measure with no family: {unknown}")

    fragile = as_bool(frame["fragile"])
    duplicate = as_bool(frame["duplicate"])
    degenerate = as_bool(frame["degenerate"])
    below = as_bool(frame["below_minimum"])
    finite_t = frame["t_newey_west"].apply(np.isfinite)
    eligible = ~fragile & ~duplicate & ~degenerate & ~below & finite_t

    by_family = {}
    leaderboard = []
    for family, group in frame.groupby("family"):
        keep = group[eligible.loc[group.index]].copy()
        keep["abs_t"] = keep["t_newey_west"].abs()
        keep = keep.sort_values(["abs_t", "id"], ascending=[False, True])
        top = keep.head(TOP_PER_FAMILY)
        rows = []
        for _, row in top.iterrows():
            rows.append({
                "cell_id": row["id"],
                "family": family,
                "target_family": row["target"],
                "rule": (f"{row['measure']} {row['transform']} {row['direction']} "
                         f"{int(row['threshold'])}"),
                "target": row["target"],
                "universe": row["universe"],
                "train_score": round(float(row["t_newey_west"]), 4),
                "train_spread_pct": round(float(row["spread_independent"]) * 100, 4),
                "train_n": int(row["n_independent"]),
                "status": "unconfirmed",
            })
        by_family[family] = {
            "tested": int(len(group)),
            "eligible": int(eligible.loc[group.index].sum()),
            "survivors": len(rows),
            "threshold_now": deflated(len(group)),
            "leaderboard": rows,
        }
        leaderboard.extend(rows)

    listed_ids = [r["cell_id"] for r in leaderboard]
    if len(listed_ids) != len(set(listed_ids)):
        raise SystemExit("a cell is listed twice")
    scored_ids = set(frame["id"])
    missing = [c for c in listed_ids if c not in scored_ids]
    if missing:
        raise SystemExit(f"listed cell absent from the scored file: {missing[:3]}")
    listed = frame[frame["id"].isin(listed_ids)]
    if as_bool(listed["fragile"]).any() or as_bool(listed["duplicate"]).any():
        raise SystemExit("a listed cell is fragile or a duplicate")
    if sum(v["tested"] for v in by_family.values()) != len(frame):
        raise SystemExit("family counts do not add up")
    for family, block in by_family.items():
        if block["survivors"] > TOP_PER_FAMILY:
            raise SystemExit(f"{family} holds more than {TOP_PER_FAMILY}")

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(SCORED.relative_to(ROOT)),
        "library_version": LIBRARY_VERSION,
        "train_period_hash": str(frame["train_period_hash"].iloc[0]),
        "cells_enumerated": int(space["cells"]),
        "cells_tested": int(len(frame)),
        "cells_skipped": int(space["skipped"]),
        "fragile": int(fragile.sum()),
        "duplicates": int(duplicate.sum()),
        "degenerate": int(degenerate.sum()),
        "below_minimum": int(below.sum()),
        "eligible": int(eligible.sum()),
        "by_family": [
            {"family": family, "tested": block["tested"],
             "survivors": block["survivors"],
             "threshold_now": block["threshold_now"]}
            for family, block in sorted(by_family.items())
        ],
        "leaderboard": leaderboard,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")

    summary = {
        "as_of": payload["as_of"],
        "today": today,
        "candidate": "s4_leaderboard",
        "source": payload["source"],
        "rows_read": int(len(frame)),
        "duplicate_ids": 0,
        "cells_enumerated": payload["cells_enumerated"],
        "cells_tested": payload["cells_tested"],
        "cells_skipped": payload["cells_skipped"],
        "fragile": payload["fragile"],
        "duplicates": payload["duplicates"],
        "degenerate": payload["degenerate"],
        "below_minimum": payload["below_minimum"],
        "eligible": payload["eligible"],
        "listed": len(leaderboard),
        "by_family": payload["by_family"],
        "top": sorted(leaderboard, key=lambda r: abs(r["train_score"]), reverse=True)[:10],
        "validation_read": False,
        "test_read": False,
        "admitted": False,
    }
    RESULTS.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({
        "rows_read": summary["rows_read"], "eligible": summary["eligible"],
        "listed": summary["listed"], "families": len(by_family),
        "top_id": summary["top"][0]["cell_id"],
        "top_score": summary["top"][0]["train_score"],
    }))


if __name__ == "__main__":
    main()
