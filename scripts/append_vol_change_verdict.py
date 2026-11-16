"""Append the btc_vol_change_7d_bottom verdict and update the backlog.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_btc_vol_change_7d_bottom.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT_A = (
    "4. btc_vol_change_7d_bottom. The 7-day change in BTC 14-day realized vol "
    "at its trailing one-year 10th percentile, against the amended bottom "
    "event. Pre-registered in research/generated.md. Not yet scored.\n"
)
OLD_NEXT_B = (
    "5. btc_vol_change_7d_bottom. The 7-day change in BTC 14-day realized vol "
    "at its trailing one-year 10th percentile, against the amended bottom "
    "event. Pre-registered in research/generated.md. Not yet scored.\n"
)
NEW_NEXT = (
    "4. btc_funding_level_pct_bottom. The BTC funding close at its trailing "
    "one-year 10th percentile, against the amended bottom event. "
    "Pre-registered in research/generated.md. Not yet scored.\n"
)
OLD_QUEUE = (
    "18. btc_vol_change_7d_bottom. The 7-day change in BTC 14-day realized vol "
    "at its trailing one-year 10th percentile, against the amended bottom "
    "event. Score 13. Pre-registered 2026-11-16 in research/generated.md. "
    "Not yet scored. Extends the 2026-11-16 btc_realized_vol_percentile_top "
    "verdict, which was insufficient on the top label, by changing the "
    "transform and the target.\n"
)
NEW_QUEUE = (
    "18. btc_vol_change_7d_bottom. Verdict 2026-11-16: insufficient. The 7-day "
    "percent change in BTC 14-day realized vol at its trailing one-year 10th "
    "percentile, against the amended bottom event. 4 fires across train and "
    "validation on BTC, below 30. "
    "results/2026-11-16_btc_vol_change_7d_bottom.json.\n"
)


def fmt(value):
    if value is None:
        return "absent"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def main() -> None:
    record = json.loads(RESULT.read_text())
    btc = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["primary"])
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "bottom_30_20_7" and r["primary"])
    train = btc["score"]["by_period"]["train"]
    validation = btc["score"]["by_period"]["validation"]
    eth_train = eth["score"]["by_period"]["train"]
    eth_val = eth["score"]["by_period"]["validation"]
    base = record["base_rates"]["BTC"]["bottom_30_20_7"]
    boot = btc["bootstrap"]["validation"]
    if btc["verdict"] != "insufficient" or btc["train_val_fires"] != 4:
        raise SystemExit(f"unexpected verdict {btc['verdict']} n {btc['train_val_fires']}")
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-15":
        raise SystemExit("results file is not today's")

    verdict = (
        "\nVerdict: insufficient. BTC has 4 fires across train and validation, "
        f"{train['fires']} and {validation['fires']}, below the 30 the bar "
        "requires, so no lift exists to quote: train lift is "
        f"{fmt(train['lift'])} on {train['fires']} fires and {train['hits']} "
        f"hits against a base rate of {fmt(train['base_rate'])} over "
        f"{train['base_fires']} episode starts, and the validation lift is "
        f"absent on {validation['fires']} fires against a base rate of "
        f"{fmt(validation['base_rate'])} over {validation['base_fires']} "
        "episode starts. The validation bootstrap interval is not quotable: "
        f"it rests on {boot['n']} episode starts and {boot['draws']} of 2,000 "
        "draws, below the half the scorer itself requires. Both neighbour cuts "
        "have zero validation fires, so the neighbour check fails. ETH at the "
        f"same cut is {eth['train_val_fires']} fires, {eth_train['fires']} in "
        f"train and {eth_val['fires']} in validation, train lift "
        f"{fmt(eth_train['lift'])}, and its neighbours do not hold. Test holds "
        "zero fires on BTC and 2 on ETH, so the cell stays test pending and is "
        "not scored as a pass or a fail. The bottom label has "
        f"{base['episodes']} episodes on BTC and {base['worst_year']} holds "
        f"{fmt(base['worst_share'])} of them, under half, so no year caveat "
        "attaches. The score is unchanged. Sixty-one tests since the last "
        "admission. results/2026-11-16_btc_vol_change_7d_bottom.json.\n\n"
    )
    log = LOG.read_text()
    marker = (
        "Expected independent n: about 30 to 50 episodes on BTC, which is thin. "
        "Assets: BTC, and ETH as the second asset. This extends the 2026-11-16 "
        "btc_realized_vol_percentile_top verdict, which was insufficient, not "
    )
    if marker not in log and "btc_vol_change_7d_bottom" not in log.split("## 2026-11-16, verdict: L1", 1)[0]:
        header = (
            "## 2026-11-16, pre-registered before any computation: "
            "btc_vol_change_7d_bottom\n\n"
            "Candidate: btc_vol_change_7d_bottom. Hypothesis: the level of "
            "realized vol was insufficient against the top event, and a falling "
            "vol after a spike is the capitulation shape, which is a different "
            "transform and a different target. Rule: the 7-day percent change "
            "in BTC 14-day realized vol, lagged one bar, at or below its own "
            "trailing one-year 10th percentile, neighbours at the 5th and the "
            "15th. The label is the amended bottom event. Horizon: 30 days. "
            "Pass: the same bar as item 1 of the 2026-11-05 list. "
            "Expected independent n: about 30 to 50 episodes on BTC, which is "
            "thin. Assets: BTC, and ETH as the second asset. This extends the "
            "2026-11-16 btc_realized_vol_percentile_top verdict, which was "
            "insufficient, not a rejection.\n"
        )
        log = header + verdict + log
    else:
        raise SystemExit("log already has a vol-change entry; refusing to guess")
    LOG.write_text(log)

    backlog = BACKLOG.read_text()
    if OLD_NEXT_A not in backlog or OLD_NEXT_B not in backlog:
        raise SystemExit("next-ten lines missing")
    if OLD_QUEUE not in backlog:
        raise SystemExit("queue line missing")
    backlog = backlog.replace(OLD_NEXT_A, NEW_NEXT, 1).replace(OLD_NEXT_B, "", 1)
    backlog = backlog.replace(OLD_QUEUE, NEW_QUEUE, 1)
    note = (
        "\nbtc_vol_change_7d_bottom was scored on 2026-11-16 and is insufficient: "
        "4 fires across train and validation on BTC at the 10th percentile of "
        "the 7-day percent change in 14-day realized vol, below 30, and "
        "validation has zero fires. results/2026-11-16_btc_vol_change_7d_bottom.json.\n"
    )
    blocked = (
        "\n- L2. Puller daemon on the laevitas bucket: perpetuals per instrument "
        "for all 13 exchanges, then futures, options and liquidations. Blocked "
        "2026-11-16: the store covers 2537 of 5185 perpetuals, 48.93 percent, "
        "and all 13 exchanges are below 95 percent. The puller is alive and "
        "working, so this waits on the daemon. The futures, options and "
        "liquidation stores do not exist yet.\n"
    )
    if "- L2. Puller daemon" not in backlog:
        raise SystemExit("L2 line missing")
    backlog = backlog.replace(
        "- L2. Puller daemon on the laevitas bucket: perpetuals per instrument "
        "for all 13 exchanges, then futures, options and liquidations. Done when "
        "the perpetual store covers 95 percent of instruments on all 13 exchanges "
        "and the futures, options and liquidation stores have their inventories.\n",
        blocked, 1)
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
