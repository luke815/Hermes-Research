"""Draft the next pooled candidates from the cross-sectional sweep.

The backlog has no item left without a verdict and no build item pending, so
this run generates. It reads results/sweeps/2026-11-19_xs_vec.csv, keeps the
best cell of each measure, drops the families the backlog already rejected,
and appends the top two to research/generated.md and to the backlog queue.
It scores nothing. The numbers in the text are read from the sweep file.
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(ROOT, "results", "sweeps", "2026-11-19_xs_vec.csv")
GENERATED = os.path.join(ROOT, "research", "generated.md")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
TODAY = "2026-11-21"

# Long/short ratios have a verdict, and the funding persistence family is
# closed. Regenerating either would be a retry, not a candidate.
BANNED = {"ls_ratio_level", "ls_ratio_chg_7",
          "funding_persist_high", "funding_persist_low"}
MIN_N = 40
KEEP = 2


def load():
    frame = pd.read_csv(SWEEP)
    for column in ("below_minimum", "degenerate", "duplicate"):
        frame[column] = frame[column].astype(str).str.lower().isin(["true", "1"])
    keep = (~frame["below_minimum"] & ~frame["degenerate"] & ~frame["duplicate"]
            & (frame["n_independent"] >= MIN_N)
            & ~frame["measure"].isin(BANNED))
    rows = frame[keep].copy()
    rows["abs_t"] = rows["t_newey_west"].abs()
    best = rows.sort_values("abs_t", ascending=False).groupby("measure").head(1)
    return best.sort_values("abs_t", ascending=False).head(KEEP)


def entry(rank, row):
    measure = row["measure"]
    horizon = int(str(row["target"]).split("_")[-1])
    spread = float(row["spread_independent"])
    side = "lower" if spread < 0 else "higher"
    return (
        f"{rank}. xs_{measure}_{row['transform']}_{row['direction']}"
        f"_{int(row['threshold'])}_{row['target']}. "
        f"Train t-stat {float(row['t_newey_west']):.4f} on "
        f"{int(row['n_independent'])} independent dates, read from "
        f"results/sweeps/2026-11-19_xs_vec.csv.\n"
        f"Hypothesis: the cross-sectional reading of {measure} at this "
        f"extreme precedes a {side} forward return on the point-in-time "
        f"universe, and the edge keeps its sign out of sample. The train "
        f"spread is {spread:.6f}.\n"
        f"Rule: cell {measure}|{row['transform']}|{row['direction']}|"
        f"{int(row['threshold'])}|{row['target']}|pit_cross_section|none|"
        f"daily, scored on data/panel_xs_laevitas, one row per coin, names "
        f"below 20,000,000 dollars of prior-bar open interest dropped, net "
        f"of per-leg costs and carry. A missing carry drops the date. The "
        f"feature is lagged one bar.\n"
        f"Horizon: {horizon} days, non-overlapping. Pass: the spread keeps "
        f"its sign in validation and in test, the non-overlapping t-stat "
        f"reaches 2 in both, and each holds at least 40 independent dates. "
        f"Below 40 is insufficient. A sign flip is rejected. Expected "
        f"independent n: the train count is {int(row['n_independent'])} on "
        f"{int(row['names'])} names; the held-out halves are shorter.\n"
    )


def main():
    chosen = load()
    if len(chosen) < KEEP:
        raise SystemExit(f"only {len(chosen)} measures survived the screen")
    generated = open(GENERATED).read()
    marker = f"## Added {TODAY}"
    if marker in generated:
        raise SystemExit("candidates for today are already written")
    block = [f"\n## Added {TODAY}\n",
             "The backlog had no item left without a verdict and no build "
             "item pending. These two are the strongest measures in "
             "results/sweeps/2026-11-19_xs_vec.csv, one cell per measure, "
             "after dropping the long/short ratio and the funding "
             "persistence family, both of which already have verdicts. "
             "Neither is scored in this run.\n"]
    backlog = open(BACKLOG).read()
    queue = []
    for number, (_, row) in enumerate(chosen.iterrows(), start=21):
        block.append("\n" + entry(number, row))
        queue.append(
            f"\n- G{number}. xs_{row['measure']}_{row['transform']}_"
            f"{row['direction']}_{int(row['threshold'])}_{row['target']}. "
            f"Pre-registered {TODAY} in research/generated.md, item "
            f"{number}. Not yet scored. Cross-sectional, on "
            f"data/panel_xs_laevitas.\n")
    open(GENERATED, "w").write(generated.rstrip("\n") + "\n" + "".join(block))
    anchor = "## A7(1) pre-registration"
    if anchor not in backlog:
        raise SystemExit("queue anchor missing")
    open(BACKLOG, "w").write(
        backlog.replace(anchor, "".join(queue) + "\n" + anchor, 1))
    print(f"wrote {len(chosen)} candidates")


if __name__ == "__main__":
    main()
