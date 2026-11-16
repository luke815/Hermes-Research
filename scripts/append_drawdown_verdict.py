"""Append the btc_drawdown_90_bottom verdict and update the backlog.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_btc_drawdown_90_bottom.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "1. btc_funding_persistence_top. Five or more days of BTC funding above its "
    "own trailing 80th percentile, against the amended top event. The C1 rerun "
    "it depended on is done.\n"
    "2. btc_drawdown_90_bottom. Drawdown from the 90-day high at its trailing "
    "10th percentile, against the amended bottom event. The C1 rerun it depended "
    "on is done.\n"
    "3. btc_realized_vol_percentile_top. 30-day realized vol at its trailing 90th "
    "percentile, against the amended top event. The C1 rerun it depended on is done.\n"
)
NEW_NEXT = (
    "1. btc_realized_vol_percentile_top. 30-day realized vol at its trailing 90th "
    "percentile, against the amended top event. The C1 rerun it depended on is done.\n"
)
OLD_QUEUE = (
    "7. btc_drawdown_90_bottom. Drawdown from the 90-day high at its trailing 10th "
    "percentile, scored against the amended bottom event. Score 18. Depends on the "
    "C1 rerun.\n"
)
NEW_QUEUE = (
    "7. btc_drawdown_90_bottom. Verdict 2026-11-16: insufficient. Close over the "
    "trailing 90-day high at its trailing one-year 10th percentile, against the "
    "amended bottom event. 10 fires across train and validation on BTC, below 30. "
    "results/2026-11-16_btc_drawdown_90_bottom.json.\n"
)


def main() -> None:
    record = json.loads(RESULT.read_text())
    row = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["primary"])
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "bottom_30_20_7" and r["primary"])
    train = row["score"]["by_period"]["train"]
    validation = row["score"]["by_period"]["validation"]
    test = row["score"]["by_period"]["test"]
    eth_train = eth["score"]["by_period"]["train"]
    eth_val = eth["score"]["by_period"]["validation"]
    base = record["base_rates"]["BTC"]["bottom_30_20_7"]
    boot = row["bootstrap"]["validation"]
    if row["verdict"] != "insufficient" or row["train_val_fires"] != 10:
        raise SystemExit(f"unexpected verdict {row['verdict']} n {row['train_val_fires']}")
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-14":
        raise SystemExit("results file is not today's")

    verdict = (
        "\nVerdict: insufficient. BTC has 10 fires across train and validation, "
        f"5 and {validation['fires']}, below the 30 the bar requires, and the "
        f"validation lift is {validation['lift']}, which is the base rate. Train "
        f"lift is {train['lift']} on {train['fires']} fires and {train['hits']} hits "
        f"against a base rate of {train['base_rate']} over {train['base_fires']} episode "
        "starts. The validation bootstrap interval is not quotable: it rests on "
        f"{boot['n']} episode starts and {boot['draws']} of 2,000 draws, below the "
        "half the scorer itself requires. The 5th percentile neighbour also has a "
        "validation lift of 1.0, so the neighbour check fails. ETH at the same cut "
        f"is {eth['train_val_fires']} fires, {eth_train['fires']} in train and "
        f"{eth_val['fires']} in validation, lift {eth_train['lift']} and "
        f"{eth_val['lift']}, and its neighbours keep the sign, but it is under 30 "
        "as well. Test holds zero fires on both names, so the cell stays test "
        "pending and is not scored as a pass or a fail. The bottom label has 22 "
        f"episodes on BTC and 2022 holds {base['worst_share']} of them, under half, "
        "so no year caveat attaches. The score is unchanged. Fifty-five tests since "
        "the last admission. results/2026-11-16_btc_drawdown_90_bottom.json.\n\n"
    )
    log = LOG.read_text()
    marker = "Expected independent n: about 30 to 50 episodes on BTC, which is thin, so a cell under 30 is reported as insufficient and not quoted. The 2021 caveat on the top label does not apply here; the bottom label's own year share is reported.\n"
    if marker not in log:
        raise SystemExit("pre-registration marker missing")
    if "Verdict: insufficient. BTC has 10 fires" in log:
        raise SystemExit("verdict already written")
    log = log.replace(marker, marker + verdict, 1)
    LOG.write_text(log)

    backlog = BACKLOG.read_text()
    if OLD_NEXT not in backlog:
        raise SystemExit("next-ten block missing")
    if OLD_QUEUE not in backlog:
        raise SystemExit("queue line missing")
    backlog = backlog.replace(OLD_NEXT, NEW_NEXT, 1).replace(OLD_QUEUE, NEW_QUEUE, 1)
    note = (
        "\nbtc_funding_persistence_top was skipped on 2026-11-16, not retested. "
        "The C2 rerun scored funding_streak_high_5d on the amended top label and "
        "closed it as insufficient: 3 fires in train and none in validation. "
        "btc_drawdown_90_bottom was scored the same day and is insufficient, 10 "
        "fires across train and validation on BTC.\n"
    )
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
