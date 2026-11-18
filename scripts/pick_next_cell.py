"""Pick the next confirmation cell. Reads the leaderboard and the record only.

A neighbour of a closed cell is the same measure with an adjacent threshold,
an adjacent change lookback, an adjacent z-score window, or an adjacent
horizon of the same kind. This script scores nothing.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "results" / "sweeps" / "leaderboard.json"
RECORD = ROOT / "results" / "sweeps" / "confirmations.json"

THRESHOLDS = [5, 10, 20, 80, 90, 95]
CHANGE = ["chg_3", "chg_7", "chg_30"]
ZSCORE = ["z_30", "z_90"]
HORIZON = {"ret": ["ret_1", "ret_3", "ret_10"], "rel": ["rel_1", "rel_3", "rel_10"]}


def adjacent(value, ladder):
    if value not in ladder:
        return []
    i = ladder.index(value)
    out = []
    if i > 0:
        out.append(ladder[i - 1])
    if i + 1 < len(ladder):
        out.append(ladder[i + 1])
    return out


def _differs(candidate, closed, field):
    return candidate[field] != closed[field]


def is_neighbour(candidate, closed):
    """Same measure, and the only difference is one adjacent axis.

    Two differences still count when one of them is itself adjacent. A
    3-day lookback at a 10-day horizon is a way around a closed 7-day,
    3-day-horizon cell, and the rule exists to stop exactly that.
    """
    if candidate["measure"] != closed["measure"]:
        return False
    if candidate["universe"] != closed["universe"]:
        return False
    if candidate["direction"] != closed["direction"]:
        return False
    kind = closed["target"].split("_")[0]
    axes = {
        "threshold": candidate["threshold"] in adjacent(closed["threshold"], THRESHOLDS),
        "change_lookback": candidate["transform"] in adjacent(closed["transform"], CHANGE),
        "zscore_window": candidate["transform"] in adjacent(closed["transform"], ZSCORE),
        "horizon": candidate["target"] in adjacent(closed["target"], HORIZON.get(kind, [])),
    }
    diffs = []
    if _differs(candidate, closed, "threshold") and not axes["threshold"]:
        diffs.append("threshold")
    if _differs(candidate, closed, "transform") and not (axes["change_lookback"] or axes["zscore_window"]):
        diffs.append("transform")
    if _differs(candidate, closed, "target") and not axes["horizon"]:
        diffs.append("target")
    return not diffs and any(axes.values())


def parse(cell_id):
    measure, transform, direction, threshold, target, universe, conditioning, timeframe = cell_id.split("|")
    return {
        "measure": measure, "transform": transform, "direction": direction,
        "threshold": int(threshold), "target": target, "universe": universe,
        "conditioning": conditioning, "timeframe": timeframe, "cell_id": cell_id,
    }


def main():
    board = json.loads(BOARD.read_text())
    record = json.loads(RECORD.read_text()) if RECORD.exists() else []
    attempted = {row["cell_id"] for row in record}
    closed = [parse(row["cell_id"]) for row in record if row["verdict"] == "rejected"]
    rows = sorted(board["leaderboard"], key=lambda r: abs(r["train_score"]), reverse=True)
    family_n = {block["family"]: block["tested"] for block in board["by_family"]}
    skipped = []
    chosen = None
    for row in rows:
        if row["cell_id"] in attempted:
            skipped.append({"cell_id": row["cell_id"], "reason": "already attempted"})
            continue
        cell = parse(row["cell_id"])
        hits = [c["cell_id"] for c in closed if is_neighbour(cell, c)]
        if hits:
            skipped.append({"cell_id": row["cell_id"], "reason": "neighbour of " + hits[0]})
            continue
        chosen = row
        break
    if chosen is None:
        print(json.dumps({"chosen": None, "skipped": len(skipped)}))
        return
    print(json.dumps({
        "cell_id": chosen["cell_id"],
        "family": chosen["family"],
        "family_n": family_n[chosen["family"]],
        "train_score": chosen["train_score"],
        "train_spread_pct": chosen["train_spread_pct"],
        "train_n": chosen["train_n"],
        "rule": chosen["rule"],
        "target": chosen["target"],
        "universe": chosen["universe"],
        "skipped_ahead": skipped,
    }, indent=2))


if __name__ == "__main__":
    main()
