"""Append the btc_funding_gap_bottom verdict and update the backlog.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_btc_funding_gap_bottom.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "3. stablecoin_supply_30d_bottom. Stablecoin supply 30-day change at its "
    "trailing 90th percentile, against the amended bottom event. Needs a "
    "DefiLlama pull first.\n"
)
NEW_NEXT = (
    "3. stablecoin_supply_30d_bottom. Stablecoin supply 30-day change at its "
    "trailing 90th percentile, against the amended bottom event. Needs a "
    "DefiLlama pull first. A pull is forbidden in a research run, so this waits.\n"
    "4. eth_drawdown_90_bottom. ETH close over its trailing 90-day high at its "
    "trailing one-year 10th percentile, against the amended bottom event. "
    "Pre-registered in research/generated.md.\n"
)
OLD_QUEUE = (
    "12. btc_funding_gap_bottom. The 7-day change in the BTC minus ETH funding "
    "gap at its trailing one-year 90th percentile, against the amended bottom "
    "event. Score 15. Pre-registered 2026-11-16 in research/generated.md. Not "
    "yet scored.\n"
)
NEW_QUEUE = (
    "12. btc_funding_gap_bottom. Verdict 2026-11-16: insufficient. The 7-day "
    "change in the BTC minus ETH funding gap at its trailing one-year 90th "
    "percentile, against the amended bottom event. 19 fires across train and "
    "validation on BTC, below 30. "
    "results/2026-11-16_btc_funding_gap_bottom.json.\n"
)


def main() -> None:
    record = json.loads(RESULT.read_text())
    row = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["primary"])
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "bottom_30_20_7" and r["primary"])
    train = row["score"]["by_period"]["train"]
    validation = row["score"]["by_period"]["validation"]
    eth_train = eth["score"]["by_period"]["train"]
    eth_val = eth["score"]["by_period"]["validation"]
    base = record["base_rates"]["BTC"]["bottom_30_20_7"]
    boot = row["bootstrap"]["validation"]
    if row["verdict"] != "insufficient" or row["train_val_fires"] != 19:
        raise SystemExit(f"unexpected verdict {row['verdict']} n {row['train_val_fires']}")
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-15":
        raise SystemExit("results file is not today's")
    if not record["lookahead_holds"].get("BTC") or not record["lookahead_holds"].get("ETH"):
        raise SystemExit("lookahead did not hold")

    verdict = (
        "\nVerdict: insufficient. BTC has 19 fires across train and validation, "
        f"{train['fires']} and {validation['fires']}, below the 30 the bar requires, "
        f"and the validation lift is {validation['lift']}, which is the base rate. "
        f"Train lift is {train['lift']} on {train['fires']} fires and {train['hits']} "
        f"hits against a base rate of {train['base_rate']} over {train['base_fires']} "
        "episode starts. The validation bootstrap interval is not quotable: it rests "
        f"on {boot['n']} episode starts and {boot['draws']} of 2,000 draws, below the "
        "half the scorer itself requires. The 85th percentile neighbour also has a "
        "validation lift of 1.0, so the neighbour check fails. ETH at the same cut is "
        f"{eth['train_val_fires']} fires, {eth_train['fires']} in train and "
        f"{eth_val['fires']} in validation, lift {eth_train['lift']} and "
        f"{eth_val['lift']}, and its neighbours do not hold either. Test holds zero "
        "fires on BTC and 2 on ETH, so the cell stays test pending and is not scored "
        "as a pass or a fail. The bottom label has 22 episodes on BTC and 2022 holds "
        f"{base['worst_share']} of them, under half, so no year caveat attaches. The "
        "score is unchanged. Fifty-seven tests since the last admission. "
        "results/2026-11-16_btc_funding_gap_bottom.json.\n\n"
    )
    log = LOG.read_text()
    marker = ("Expected independent n: about 30 to 50 episodes on BTC, which is thin, "
              "so a cell under 30 is reported as insufficient and not quoted. The "
              "bottom label's year share is reported.\n")
    if marker not in log:
        raise SystemExit("pre-registration marker missing")
    if "Verdict: insufficient. BTC has 19 fires" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(log.replace(marker, marker + verdict, 1))

    backlog = BACKLOG.read_text()
    if OLD_NEXT not in backlog:
        raise SystemExit("next-ten block missing")
    if OLD_QUEUE not in backlog:
        raise SystemExit("queue line missing")
    note = (
        "\nbtc_funding_gap_bottom was scored on 2026-11-16 and is insufficient: "
        "19 fires across train and validation on BTC at the 90th percentile of the "
        "7-day funding-gap change, below 30, and the validation lift is 1.0. "
        "results/2026-11-16_btc_funding_gap_bottom.json.\n"
    )
    backlog = backlog.replace(OLD_NEXT, NEW_NEXT, 1).replace(OLD_QUEUE, NEW_QUEUE, 1)
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
