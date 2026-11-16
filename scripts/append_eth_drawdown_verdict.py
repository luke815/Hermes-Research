"""Append the eth_drawdown_90_bottom verdict and update the backlog.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_eth_drawdown_90_bottom.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "4. eth_drawdown_90_bottom. ETH close over its trailing 90-day high at its "
    "trailing one-year 10th percentile, against the amended bottom event. "
    "Pre-registered in research/generated.md.\n"
)
NEW_NEXT = (
    "4. btc_basis_gap_chg7_bottom. The 7-day change in the BTC minus ETH basis "
    "gap at its trailing one-year 90th percentile, against the amended bottom "
    "event. Pre-registered in research/generated.md. Not yet scored.\n"
)
OLD_QUEUE = (
    "13. eth_drawdown_90_bottom. ETH close over its trailing 90-day high at its "
    "trailing one-year 10th percentile, against the amended bottom event. Score "
    "14. Extends the BTC cell that was insufficient on 2026-11-16 by changing "
    "the asset. Not yet scored.\n"
)
NEW_QUEUE = (
    "13. eth_drawdown_90_bottom. Verdict 2026-11-16: insufficient. ETH close "
    "over the trailing 90-day high at its trailing one-year 10th percentile, "
    "against the amended bottom event. 14 fires across train and validation on "
    "ETH, below 30. results/2026-11-16_eth_drawdown_90_bottom.json.\n"
)


def main() -> None:
    record = json.loads(RESULT.read_text())
    eth = next(r for r in record["rows"]
               if r["asset"] == "ETH" and r["label"] == "bottom_30_20_7" and r["primary"])
    btc = next(r for r in record["rows"]
               if r["asset"] == "BTC" and r["label"] == "bottom_30_20_7" and r["primary"])
    train = eth["score"]["by_period"]["train"]
    validation = eth["score"]["by_period"]["validation"]
    test = eth["score"]["by_period"]["test"]
    btc_train = btc["score"]["by_period"]["train"]
    btc_val = btc["score"]["by_period"]["validation"]
    base = record["base_rates"]["ETH"]["bottom_30_20_7"]
    boot = eth["bootstrap"]["validation"]
    if eth["verdict"] != "insufficient" or eth["train_val_fires"] != 14:
        raise SystemExit(f"unexpected verdict {eth['verdict']} n {eth['train_val_fires']}")
    if record["today"] != "2026-11-16" or record["panel_end"] != "2026-11-15":
        raise SystemExit("results file is not today's")

    verdict = (
        "\nVerdict: insufficient. ETH has 14 fires across train and validation, "
        f"{train['fires']} and {validation['fires']}, below the 30 the bar "
        f"requires, and the validation lift is {validation['lift']} on "
        f"{validation['fires']} fires and {validation['hits']} hits against a "
        f"base rate of {validation['base_rate']} over {validation['base_fires']} "
        f"episode starts. Train lift is {train['lift']} on {train['fires']} fires "
        f"and {train['hits']} hits against a base rate of {train['base_rate']} "
        f"over {train['base_fires']} episode starts. The validation bootstrap "
        "interval is not quotable: it rests on "
        f"{boot['n']} episode starts and {boot['draws']} of 2,000 draws, below "
        "the half the scorer itself requires. Both neighbour cuts keep the sign, "
        "lift 1.333333 at the 5th and the 15th, but the cell never reaches the "
        "episode bar, so the neighbour check does not rescue it. BTC at the same "
        f"cut is {btc['train_val_fires']} fires, {btc_train['fires']} in train and "
        f"{btc_val['fires']} in validation, lift {btc_train['lift']} and "
        f"{btc_val['lift']}, and its neighbours do not hold. Test holds zero fires "
        "on both names, so the cell stays test pending and is not scored as a "
        "pass or a fail. The bottom label has 26 episodes on ETH and 2022 holds "
        f"{base['worst_share']} of them, under half, so no year caveat attaches. "
        "The score is unchanged. Fifty-eight tests since the last admission. "
        "results/2026-11-16_eth_drawdown_90_bottom.json.\n\n"
    )
    log = LOG.read_text()
    marker = (
        "Expected independent n: about 30 to 50 episodes on ETH, which is thin, "
        "so a cell under 30 is reported as insufficient and not quoted. The "
        "bottom label's own year share is reported. This extends the 2026-11-16 "
        "btc_drawdown_90_bottom verdict, which was insufficient, not a "
        "rejection.\n"
    )
    if marker not in log:
        raise SystemExit("pre-registration marker missing")
    if "Verdict: insufficient. ETH has 14 fires" in log:
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
        "\neth_drawdown_90_bottom was scored on 2026-11-16 and is insufficient: "
        "14 fires across train and validation on ETH at the 10th percentile of "
        "the close over the trailing 90-day high, below 30, and the validation "
        "bootstrap rests on 4 episode starts. "
        "results/2026-11-16_eth_drawdown_90_bottom.json.\n"
    )
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
