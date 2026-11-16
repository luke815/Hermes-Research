"""Record the eth_btc_ratio_z90_bottom verdict and refill the queue.

Numbers are read from the results file written this run. Nothing is recomputed.
The two new candidates are pre-registered and not scored.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_eth_btc_ratio_z90_bottom.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"
GENERATED = ROOT / "research" / "generated.md"

MARKER = (
    "Expected independent n: about 30 to 50 episodes on BTC, which is thin, "
    "so a cell under 30 is reported as insufficient and not quoted. The bottom "
    "label's year share is reported.\n"
)


def main() -> None:
    record = json.loads(RESULT.read_text())
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-15":
        raise SystemExit("results file is not today's")
    if record["lookahead_holds"] != {"BTC": True, "ETH": True}:
        raise SystemExit("lookahead did not hold")
    if record["factor_observations"] != 2466:
        raise SystemExit("factor count moved")

    btc = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["primary"])
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "bottom_30_20_7" and r["primary"])
    if btc["verdict"] != "insufficient" or btc["train_val_fires"] != 2:
        raise SystemExit(f"unexpected btc {btc['verdict']} {btc['train_val_fires']}")
    if eth["verdict"] != "insufficient" or eth["train_val_fires"] != 6:
        raise SystemExit(f"unexpected eth {eth['verdict']} {eth['train_val_fires']}")

    train = btc["score"]["by_period"]["train"]
    validation = btc["score"]["by_period"]["validation"]
    eth_train = eth["score"]["by_period"]["train"]
    eth_val = eth["score"]["by_period"]["validation"]
    eth_test = eth["score"]["by_period"]["test"]
    base = record["base_rates"]["BTC"]["bottom_30_20_7"]
    boot = btc["bootstrap"]["validation"]
    eth_boot = eth["bootstrap"]["validation"]
    neigh = next(r for r in record["rows"]
                 if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["cut"] == 0.15)

    verdict = (
        "\nVerdict: insufficient. BTC has 2 fires across train and validation, "
        f"{train['fires']} and {validation['fires']}, below the 30 the bar "
        f"requires, and the validation lift is missing because validation has "
        f"zero fires against a base rate of {validation['base_rate']} over "
        f"{validation['base_fires']} episode starts. Train lift is "
        f"{train['lift']} on {train['fires']} fires and {train['hits']} hits "
        f"against a base rate of {train['base_rate']} over {train['base_fires']} "
        "episode starts. The validation bootstrap interval is not quotable: it "
        f"rests on {boot['n']} episode starts and {boot['draws']} of 2,000 "
        "draws, below the half the scorer itself requires. The 5th percentile "
        "neighbour also has zero validation fires, so the neighbour check fails "
        f"even though the 15th percentile lift is {neigh['score']['by_period']['validation']['lift']} "
        f"on {neigh['train_val_fires']} fires. ETH at the same cut is "
        f"{eth['train_val_fires']} fires, {eth_train['fires']} in train and "
        f"{eth_val['fires']} in validation, train lift {eth_train['lift']}, and "
        f"its neighbours do not hold. Its validation bootstrap rests on "
        f"{eth_boot['n']} episode starts and {eth_boot['draws']} draws. Test "
        f"holds zero fires on BTC and {eth_test['fires']} on ETH, so the cell "
        "stays test pending and is not scored as a pass or a fail. The bottom "
        f"label has {base['episodes']} episodes on BTC and {base['worst_year']} "
        f"holds {base['worst_share']} of them, under half, so no year caveat "
        "attaches. The score is unchanged. Sixty tests since the last "
        "admission. results/2026-11-16_eth_btc_ratio_z90_bottom.json.\n\n"
    )
    log = LOG.read_text()
    if MARKER not in log:
        raise SystemExit("pre-registration marker missing")
    if "Verdict: insufficient. BTC has 2 fires" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(log.replace(MARKER, MARKER + verdict, 1))

    backlog = BACKLOG.read_text()
    old_next = (
        "4. eth_btc_ratio_z90_bottom. The ETH/BTC ratio's trailing 90-day "
        "z-score at its trailing one-year 10th percentile, against the amended "
        "bottom event. Pre-registered in research/generated.md. Not yet "
        "scored.\n"
    )
    new_next = (
        "4. btc_vol_change_7d_bottom. The 7-day change in BTC 14-day realized "
        "vol at its trailing one-year 10th percentile, against the amended "
        "bottom event. Pre-registered in research/generated.md. Not yet "
        "scored.\n"
        "5. btc_funding_level_pct_bottom. The BTC funding close at its trailing "
        "one-year 10th percentile, against the amended bottom event. "
        "Pre-registered in research/generated.md. Not yet scored.\n"
        "6. btc_oi_share_chg7_top. The 7-day change in BTC's share of open "
        "interest at its trailing one-year 90th percentile, against the "
        "amended top event. Pre-registered in research/generated.md. Not yet "
        "scored. Blocked on data: the series starts 2022-09-09, so the train "
        "period is short.\n"
        "7. btc_alt_dispersion_z90_top. The 14-day alt dispersion's trailing "
        "90-day z-score at its trailing one-year 90th percentile, against the "
        "amended top event. Pre-registered in research/generated.md. Not yet "
        "scored.\n"
    )
    old_queue = (
        "17. eth_btc_ratio_z90_bottom. The ETH/BTC ratio's trailing 90-day "
        "z-score at its trailing one-year 10th percentile, against the amended "
        "bottom event. Score 13. Pre-registered 2026-11-16 in "
        "research/generated.md. Not yet scored.\n"
    )
    new_queue = (
        "17. eth_btc_ratio_z90_bottom. Verdict 2026-11-16: insufficient. The "
        "ETH/BTC ratio's trailing 90-day z-score at its trailing one-year "
        "10th percentile, against the amended bottom event. 2 fires across "
        "train and validation on BTC, below 30, and validation has zero fires. "
        "results/2026-11-16_eth_btc_ratio_z90_bottom.json.\n"
    )
    if old_next not in backlog:
        raise SystemExit("next-ten block missing")
    if old_queue not in backlog:
        raise SystemExit("queue line missing")
    backlog = backlog.replace(old_next, new_next, 1).replace(old_queue, new_queue, 1)
    note = (
        "\neth_btc_ratio_z90_bottom was scored on 2026-11-16 and is "
        "insufficient: 2 fires across train and validation on BTC at the 10th "
        "percentile of the ETH/BTC 90-day z-score, below 30, and validation "
        "has zero fires. results/2026-11-16_eth_btc_ratio_z90_bottom.json.\n"
    )
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    added = (
        "20. btc_funding_level_pct_bottom. The BTC funding close at its "
        "trailing one-year 10th percentile, against the amended bottom event. "
        "Score 14. Pre-registered 2026-11-16 in research/generated.md. Not yet "
        "scored. Extends the rejected funding-level return spread by changing "
        "the target.\n"
        "21. btc_alt_dispersion_z90_top. The 14-day alt dispersion's trailing "
        "90-day z-score at its trailing one-year 90th percentile, against the "
        "amended top event. Score 12. Pre-registered 2026-11-16 in "
        "research/generated.md. Not yet scored. Extends the 2026-11-01 "
        "dispersion_14 rejection, which flipped on the 10-day return, by "
        "changing the target.\n"
    )
    marker = "19. btc_oi_share_chg7_top. The 7-day change in BTC's share"
    at = backlog.find(marker)
    if at < 0:
        raise SystemExit("oi share line missing")
    end = backlog.find("\n", at)
    backlog = backlog[:end + 1] + added + backlog[end + 1:]
    BACKLOG.write_text(backlog)

    generated = GENERATED.read_text()
    if "btc_funding_level_pct_bottom" in generated:
        raise SystemExit("candidates already generated")
    generated += (
        "\n\n## Added 2026-11-16, fourth pass\n\n"
        "The queue had fallen to one scoreable item after "
        "eth_btc_ratio_z90_bottom was scored. stablecoin_supply_30d_bottom "
        "needs a pull and btc_oi_share_chg7_top starts 2022-09-09, so both "
        "stay blocked. Neither candidate below is tested in this run.\n\n"
        "15. btc_funding_level_pct_bottom. Score 14 (prior 4, data 5, novelty "
        "2, reach 2, cost 1).\n"
        "Hypothesis: funding at a washed-out low marks capitulation, and the "
        "level that was rejected against the 10-day return has no verdict "
        "against the bottom event. The change of the funding gap was "
        "insufficient on 2026-11-16, so this changes the measure and the "
        "target. Rule: the BTC funding close, lagged one bar by the "
        "percentile, at or below its own trailing one-year 10th percentile, "
        "neighbours at the 5th and the 15th. The label is the amended bottom "
        "event. Horizon: 30 days. Pass: the same bar as item 1 of the "
        "2026-11-05 list. Expected independent n: about 30 to 50 episodes on "
        "BTC, which is thin. Assets: BTC, and ETH as the second asset. This "
        "extends the rejected raw funding level by changing the target.\n\n"
        "16. btc_alt_dispersion_z90_top. Score 12 (prior 3, data 5, novelty 2, "
        "reach 1, cost 1).\n"
        "Hypothesis: alt dispersion blowing out marks a late-cycle tape, and "
        "the same series flipped sign on the 10-day return, so the top event "
        "is a different question rather than a retry. Rule: the trailing "
        "90-day z-score of dispersion_14, lagged one bar, at or above its own "
        "trailing one-year 90th percentile, neighbours at the 85th and the "
        "95th. The label is the amended top event. Horizon: 30 days. Pass: "
        "the same bar as item 1. Expected independent n: about 30 to 50 "
        "episodes on BTC, which is thin. Assets: BTC, and ETH as the second "
        "asset. This extends the 2026-11-01 rejection of dispersion_14, which "
        "flipped on the 10-day return, by changing the target.\n"
    )
    GENERATED.write_text(generated)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size,
          "generated", GENERATED.stat().st_size)


if __name__ == "__main__":
    main()
