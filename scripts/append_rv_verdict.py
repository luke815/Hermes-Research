"""Append the btc_realized_vol_percentile_top verdict and update the backlog.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_btc_realized_vol_percentile_top.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "1. btc_realized_vol_percentile_top. 30-day realized vol at its trailing 90th "
    "percentile, against the amended top event. The C1 rerun it depended on is done.\n"
    "2. Single-feature cross-sectional test: relative strength at 14 and 30 days, "
    "point-in-time universe, net of costs.\n"
)
NEW_NEXT = (
    "1. Single-feature cross-sectional test: relative strength at 14 and 30 days, "
    "point-in-time universe, net of costs.\n"
)
OLD_QUEUE = (
    "8. btc_realized_vol_percentile_top. 30-day realized vol at its trailing 90th "
    "percentile, scored against the amended top event. Score 17. Depends on the "
    "C1 rerun.\n"
)


def fmt(value) -> str:
    return "absent" if value is None else str(value)


def main() -> None:
    record = json.loads(RESULT.read_text())
    row = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "top_30_20" and r["primary"])
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "top_30_20" and r["primary"])
    train = row["score"]["by_period"]["train"]
    validation = row["score"]["by_period"]["validation"]
    test = row["score"]["by_period"]["test"]
    eth_train = eth["score"]["by_period"]["train"]
    eth_val = eth["score"]["by_period"]["validation"]
    base = record["base_rates"]["BTC"]["top_30_20"]
    boot = row["bootstrap"]["validation"]
    neighbour = next(r for r in record["rows"]
                     if r["asset"] == "BTC" and r["label"] == "top_30_20"
                     and r["cut"] == 0.85)
    if row["verdict"] != "insufficient" or row["train_val_fires"] != 0:
        raise SystemExit(f"unexpected verdict {row['verdict']} n {row['train_val_fires']}")
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-14":
        raise SystemExit("results file is not today's")
    if not record["lookahead_holds"]["BTC"] or not record["lookahead_holds"]["ETH"]:
        raise SystemExit("lookahead failed")

    new_queue = (
        "8. btc_realized_vol_percentile_top. Verdict 2026-11-16: insufficient. "
        "30-day realized vol at its trailing one-year 90th percentile, against the "
        "amended top event. "
        f"{row['train_val_fires']} fires across train and validation on BTC, below 30. "
        "results/2026-11-16_btc_realized_vol_percentile_top.json.\n"
    )
    verdict = (
        "\nVerdict: insufficient. BTC has "
        f"{row['train_val_fires']} fires across train and validation, "
        f"{train['fires']} and {validation['fires']}, below the 30 the bar requires, "
        f"so no lift exists to quote: train lift is {fmt(train['lift'])} and "
        f"validation lift is {fmt(validation['lift'])}. The validation bootstrap "
        f"interval is empty, {boot['draws']} draws on {boot['n']} episode starts. "
        f"The 85th percentile neighbour has {neighbour['train_val_fires']} fire and "
        "the 95th has none, so the neighbour check fails. ETH at the same cut is "
        f"{eth['train_val_fires']} fire, {eth_train['fires']} in train and "
        f"{eth_val['fires']} in validation, train lift {fmt(eth_train['lift'])}, "
        "and its neighbours do not hold. Test holds "
        f"{test['fires']} fires on BTC, so the cell is not scored as a pass or a "
        "fail. The top label has "
        f"{base['episodes']} episodes on BTC and {base['worst_year']} holds "
        f"{base['worst_share']} of them, exactly half, so the 2021 caveat from the "
        "C1 rerun attaches and this cell does not add to it. The score is unchanged. "
        "Fifty-six tests since the last admission. "
        "results/2026-11-16_btc_realized_vol_percentile_top.json.\n\n"
    )
    log = LOG.read_text()
    marker = (
        "Expected independent n: about 30 to 50 episodes on BTC, which is thin, "
        "so a cell under 30 is reported as insufficient and not quoted. The top "
        "label carries the 2021 caveat from the C1 rerun, and this result carries "
        "it too.\n"
    )
    if marker not in log:
        raise SystemExit("pre-registration marker missing")
    if "Verdict: insufficient. BTC has 0 fires" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(log.replace(marker, marker + verdict, 1))

    backlog = BACKLOG.read_text()
    if OLD_NEXT not in backlog:
        raise SystemExit("next-ten block missing")
    if OLD_QUEUE not in backlog:
        raise SystemExit("queue line missing")
    backlog = backlog.replace(OLD_NEXT, NEW_NEXT, 1).replace(OLD_QUEUE, new_queue, 1)
    note = (
        "\nbtc_realized_vol_percentile_top was scored on 2026-11-16 and is "
        "insufficient: 0 fires across train and validation on BTC at the 90th "
        "percentile of 30-day realized vol, against the amended top event.\n"
    )
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
