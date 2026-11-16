"""Record the btc_basis_gap_chg7_bottom verdict and refill the queue.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_btc_basis_gap_chg7_bottom.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"
GENERATED = ROOT / "research" / "generated.md"


def main() -> None:
    record = json.loads(RESULT.read_text())
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-15":
        raise SystemExit("results file is not today's")
    if record["lookahead_holds"] != {"BTC": True, "ETH": True}:
        raise SystemExit("lookahead did not hold")

    btc = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["primary"])
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "bottom_30_20_7" and r["primary"])
    if btc["verdict"] != "insufficient" or btc["train_val_fires"] != 18:
        raise SystemExit(f"unexpected btc verdict {btc['verdict']} n {btc['train_val_fires']}")
    if eth["verdict"] != "insufficient" or eth["train_val_fires"] != 19:
        raise SystemExit(f"unexpected eth verdict {eth['verdict']} n {eth['train_val_fires']}")

    train = btc["score"]["by_period"]["train"]
    validation = btc["score"]["by_period"]["validation"]
    eth_train = eth["score"]["by_period"]["train"]
    eth_val = eth["score"]["by_period"]["validation"]
    eth_test = eth["score"]["by_period"]["test"]
    base = record["base_rates"]["BTC"]["bottom_30_20_7"]
    boot = btc["bootstrap"]["validation"]
    eth_boot = eth["bootstrap"]["validation"]

    entry = (
        "## 2026-11-16, pre-registered before any computation: "
        "btc_basis_gap_chg7_bottom\n\n"
        "Candidate: btc_basis_gap_chg7_bottom. Hypothesis: the basis gap between "
        "BTC and ETH was rejected as a 10-day return spread, and a basis that "
        "widens in BTC while price sits near its lows is leverage arriving at a "
        "low, which is a different question from that spread. Rule: the factor "
        "is the 7-day change in the venue-mean BTC basis minus the venue-mean "
        "ETH basis, and the value ranked at day t is the prior bar's, so bar t "
        "itself never enters. The extreme is that value at or above its own "
        "trailing one-year percentile, the window ending at the prior bar, at "
        "the 90th percentile, with neighbours at the 85th and the 95th. A fire "
        "is an extreme reading on a bottom candidate day, a day within 5 percent "
        "of the trailing 60-day low. An episode counts as caught when a fire "
        "landed inside the 30 days before its start, so the hit rate and the "
        "base rate are both shares of episode starts. Horizon: 30 days. Label: "
        "the amended bottom event, a 20 percent rise within 30 days with no "
        "close in between more than 7 percent below today. Also reported, and "
        "not used to choose anything: the 30 percent rise within 60 days with a "
        "10 percent giveback. Assets: BTC alone, and ETH as the second asset. "
        "Pass: at least 30 episodes in the cell across train and validation "
        "combined, lift above 1 in validation with the episode-bootstrap 90 "
        "percent interval clear of 1, the train sign agrees, and both neighbour "
        "cuts keep the sign. The test period gates admission only once it holds "
        "ten episodes. Expected independent n: about 30 to 50 episodes on BTC, "
        "which is thin, so a cell under 30 is reported as insufficient and not "
        "quoted. The bottom label's year share is reported. This extends the "
        "2026-11-01 retest of basis_gap_btc_eth, which was rejected on the "
        "10-day return, by changing the transform and the target.\n\n"
        "Verdict: insufficient. BTC has 18 fires across train and validation, "
        f"{train['fires']} and {validation['fires']}, below the 30 the bar "
        f"requires, and the validation lift is {validation['lift']}, which is "
        f"the base rate of {validation['base_rate']} over "
        f"{validation['base_fires']} episode starts. Train lift is "
        f"{train['lift']} on {train['fires']} fires and {train['hits']} hits "
        f"against a base rate of {train['base_rate']} over {train['base_fires']} "
        "episode starts. The validation bootstrap interval is not quotable: it "
        f"rests on {boot['n']} episode starts and {boot['draws']} of 2,000 "
        "draws, below the half the scorer itself requires. Both neighbour cuts "
        "have a validation lift of 1.0, so the neighbour check fails. ETH at "
        f"the same cut is {eth['train_val_fires']} fires, {eth_train['fires']} "
        f"in train and {eth_val['fires']} in validation, lift "
        f"{eth_train['lift']} and {eth_val['lift']}, and its neighbours do not "
        f"hold. Its validation bootstrap rests on {eth_boot['n']} episode "
        f"starts and {eth_boot['draws']} draws. Test holds zero fires on BTC "
        f"and {eth_test['fires']} on ETH, so the cell stays test pending and is "
        "not scored as a pass or a fail. The bottom label has "
        f"{base['episodes']} episodes on BTC and {base['worst_year']} holds "
        f"{base['worst_share']} of them, under half, so no year caveat "
        "attaches. The score is unchanged. Fifty-nine tests since the last "
        "admission. results/2026-11-16_btc_basis_gap_chg7_bottom.json.\n\n"
    )
    log = LOG.read_text()
    if "btc_basis_gap_chg7_bottom" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(entry + log)

    backlog = BACKLOG.read_text()
    old_next = (
        "4. btc_basis_gap_chg7_bottom. The 7-day change in the BTC minus ETH "
        "basis gap at its trailing one-year 90th percentile, against the "
        "amended bottom event. Pre-registered in research/generated.md. Not "
        "yet scored.\n"
    )
    new_next = (
        "4. eth_btc_ratio_z90_bottom. The ETH/BTC ratio's trailing 90-day "
        "z-score at its trailing one-year 10th percentile, against the amended "
        "bottom event. Pre-registered in research/generated.md. Not yet "
        "scored.\n"
        "5. btc_vol_change_7d_bottom. The 7-day change in BTC 14-day realized "
        "vol at its trailing one-year 10th percentile, against the amended "
        "bottom event. Pre-registered in research/generated.md. Not yet "
        "scored.\n"
        "6. btc_oi_share_chg7_top. The 7-day change in BTC's share of open "
        "interest at its trailing one-year 90th percentile, against the "
        "amended top event. Pre-registered in research/generated.md. Not yet "
        "scored. Blocked on data: the series starts 2022-09-09, so the train "
        "period is short.\n"
    )
    old_queue = (
        "16. btc_basis_gap_chg7_bottom. The 7-day change in the BTC minus ETH "
        "basis gap at its trailing one-year 90th percentile, against the "
        "amended bottom event. Score 14. Pre-registered 2026-11-16 in "
        "research/generated.md. Not yet scored. Extends the 2026-11-01 "
        "rejection of basis_gap_btc_eth by changing the transform and the "
        "target.\n"
    )
    new_queue = (
        "16. btc_basis_gap_chg7_bottom. Verdict 2026-11-16: insufficient. The "
        "7-day change in the venue-mean BTC minus ETH basis at its trailing "
        "one-year 90th percentile, against the amended bottom event. 18 fires "
        "across train and validation on BTC, below 30, and the validation lift "
        "is 1.0. results/2026-11-16_btc_basis_gap_chg7_bottom.json.\n"
    )
    if old_next not in backlog:
        raise SystemExit("next-ten block missing")
    if old_queue not in backlog:
        raise SystemExit("queue line missing")
    backlog = backlog.replace(old_next, new_next, 1).replace(old_queue, new_queue, 1)
    note = (
        "\nbtc_basis_gap_chg7_bottom was scored on 2026-11-16 and is "
        "insufficient: 18 fires across train and validation on BTC at the 90th "
        "percentile of the 7-day basis-gap change, below 30, and the validation "
        "lift is 1.0. results/2026-11-16_btc_basis_gap_chg7_bottom.json.\n"
    )
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    added = (
        "18. btc_vol_change_7d_bottom. The 7-day change in BTC 14-day realized "
        "vol at its trailing one-year 10th percentile, against the amended "
        "bottom event. Score 13. Pre-registered 2026-11-16 in "
        "research/generated.md. Not yet scored. Extends the 2026-11-16 "
        "btc_realized_vol_percentile_top verdict, which was insufficient on "
        "the top label, by changing the transform and the target.\n"
        "19. btc_oi_share_chg7_top. The 7-day change in BTC's share of open "
        "interest at its trailing one-year 90th percentile, against the "
        "amended top event. Score 12. Pre-registered 2026-11-16 in "
        "research/generated.md. Not yet scored. Blocked on data: the series "
        "starts 2022-09-09, so the train period is short.\n"
    )
    marker = "17. eth_btc_ratio_z90_bottom. The ETH/BTC ratio's trailing "
    at = backlog.find(marker)
    if at < 0:
        raise SystemExit("ratio line missing")
    end = backlog.find("\n", at)
    backlog = backlog[:end + 1] + added + backlog[end + 1:]
    BACKLOG.write_text(backlog)

    generated = GENERATED.read_text()
    if "btc_vol_change_7d_bottom" in generated:
        raise SystemExit("candidates already generated")
    generated += (
        "\n\n## Added 2026-11-16, third pass\n\n"
        "The queue had fallen to two scoreable items after "
        "btc_basis_gap_chg7_bottom was scored. stablecoin_supply_30d_bottom "
        "and btc_oi_share_chg7_top both wait on data, and a research run never "
        "pulls. Neither candidate below is tested in this run.\n\n"
        "13. btc_vol_change_7d_bottom. Score 13 (prior 3, data 5, novelty 3, "
        "reach 1, cost 1).\n"
        "Hypothesis: the level of realized vol was insufficient against the "
        "top event, and a falling vol after a spike is the capitulation shape, "
        "which is a different transform and a different target. Rule: the "
        "7-day percent change in BTC 14-day realized vol, lagged one bar, at "
        "or below its own trailing one-year 10th percentile, neighbours at the "
        "5th and the 15th. The label is the amended bottom event. Horizon: 30 "
        "days. Pass: the same bar as item 1 of the 2026-11-05 list. Expected "
        "independent n: about 30 to 50 episodes on BTC, which is thin. Assets: "
        "BTC, and ETH as the second asset. This extends the 2026-11-16 "
        "btc_realized_vol_percentile_top verdict, which was insufficient, not "
        "a rejection, by changing the transform and the target.\n\n"
        "14. btc_oi_share_chg7_top. Score 12 (prior 3, data 2, novelty 4, "
        "reach 2, cost 1).\n"
        "Hypothesis: BTC taking a rising share of open interest marks leverage "
        "concentrating in the leader, which should precede a top rather than a "
        "bottom. The level of the share has no verdict, and the change is the "
        "transform that has not been tried. Rule: the 7-day change in "
        "btc_oi_share, lagged one bar, at or above its own trailing one-year "
        "90th percentile, neighbours at the 85th and the 95th. The label is "
        "the amended top event. Horizon: 30 days. Pass: the same bar as item "
        "1. Expected independent n: about 20 episodes, below 40, because the "
        "series starts 2022-09-09 and the train period is short. Marked "
        "insufficient by design and blocked on data until the series is longer "
        "or the universe is pooled.\n"
    )
    GENERATED.write_text(generated)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size,
          "generated", GENERATED.stat().st_size)


if __name__ == "__main__":
    main()
