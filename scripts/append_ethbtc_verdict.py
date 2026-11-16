"""Append the eth_btc_30d_conditioning verdict and update the backlog.

Numbers are read from the results file written this run. Nothing is recomputed.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_eth_btc_30d_conditioning.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "4. eth_btc_30d_conditioning. The btc_ret_30 spread split by tercile of the ETH/BTC "
    "30-day return. Expected n about 20 per cell, so report it as thin.\n"
)
NEW_NEXT = (
    "4. BTC 1-day and 3-day horizons for the four live factors, non-overlapping, "
    "net of costs, both halves, BTC and the alt basket. Not yet scored at those horizons.\n"
)
OLD_QUEUE = (
    "9. eth_btc_30d_conditioning. The btc_ret_30 spread split by tercile of the ETH/BTC "
    "30-day return. Score 16. Expected n is thin, about 20 per cell.\n"
)


def pct(cell: dict) -> str:
    value = cell["spread_pct"]
    return "none" if value is None else f"{value}%"


def main() -> None:
    record = json.loads(RESULT.read_text())
    if record["date"] != "2026-11-16" or record["panel_end"] != "2026-11-14":
        raise SystemExit("results file is not today's")
    if record["candidate"] != "eth_btc_30d_conditioning":
        raise SystemExit("wrong candidate")

    btc = record["assets"]["btc_price"]
    alt = record["assets"]["alt_price"]
    btc_u = btc["unsplit"]
    alt_u = alt["unsplit"]

    # A tercile can only be judged where both sides of the spread exist in
    # validation and in test. None does, on either asset.
    judged = []
    for asset, block in (("BTC", btc), ("alt basket", alt)):
        for label, cell in block["terciles"].items():
            validation = cell["by_period"]["validation"]
            test = cell["by_period"]["test"]
            if validation["spread_pct"] is not None or test["spread_pct"] is not None:
                judged.append(f"{asset} {label}")
    if judged:
        raise SystemExit(f"expected no judgeable cell, found {judged}")

    def line(asset: str, block: dict) -> str:
        parts = []
        for label in ("low", "mid", "high"):
            cell = block["terciles"][label]
            train = cell["by_period"]["train"]
            validation = cell["by_period"]["validation"]
            test = cell["by_period"]["test"]
            parts.append(
                f"{label} tercile {cell['independent_n']} bars, train {pct(train)} "
                f"(n={train['n']}), validation {pct(validation)} (n={validation['n']}), "
                f"test {pct(test)} (n={test['n']})"
            )
        return f"{asset}: " + "; ".join(parts) + "."

    verdict = (
        "\n## 2026-11-16, verdict: eth_btc_30d_conditioning\n\n"
        "Verdict: insufficient. No tercile of the ETH/BTC 30-day return has both sides "
        "of the btc_ret_30 spread in validation or in test, on BTC or on the alt basket, "
        "so the comparison the pass rule asks for cannot be made and nothing is admitted. "
        "The score is unchanged.\n"
        f"BTC unsplit spread: train {btc_u['train']['spread_pct']}% "
        f"(n={btc_u['train']['n']}), validation {btc_u['validation']['spread_pct']}% "
        f"(n={btc_u['validation']['n']}), test {btc_u['test']['spread_pct']}% "
        f"(n={btc_u['test']['n']}), on {btc['independent_n']} non-overlapping bars. "
        "The test sign flips to negative, but that cell holds 2 bars and is not quoted.\n"
        f"Alt basket unsplit spread: train {alt_u['train']['spread_pct']}% "
        f"(n={alt_u['train']['n']}), validation {alt_u['validation']['spread_pct']}% "
        f"(n={alt_u['validation']['n']}), test {alt_u['test']['spread_pct']}% "
        f"(n={alt_u['test']['n']}), on {alt['independent_n']} bars. The alt basket is the "
        "fixed 20 and is survivor-biased.\n"
        + line("BTC", btc) + "\n"
        + line("Alt basket", alt) + "\n"
        f"Correlation of the conditioner with the factor it splits is "
        f"{record['correlation_factor_conditioner']}, so the split is not a restatement. "
        "Every tercile cell is below 30 independent observations and is reported, not "
        "quoted. Returns are net of the thin tier because the panel has no USD open "
        "interest. Fifty-three tests since the last admission; this one is recorded and "
        "does not add to that count because it is not a confirmation attempt. "
        "results/2026-11-16_eth_btc_30d_conditioning.json.\n"
    )

    log = LOG.read_text()
    if "verdict: eth_btc_30d_conditioning" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(log + verdict)

    new_queue = (
        "9. eth_btc_30d_conditioning. Verdict 2026-11-16: insufficient. The btc_ret_30 "
        "spread split by tercile of the ETH/BTC 30-day return has no tercile with both "
        "sides of the spread in validation or test, on BTC or the alt basket. "
        "results/2026-11-16_eth_btc_30d_conditioning.json.\n"
    )
    backlog = BACKLOG.read_text()
    if OLD_NEXT not in backlog:
        raise SystemExit("next-ten block missing")
    if OLD_QUEUE not in backlog:
        raise SystemExit("queue line missing")
    backlog = backlog.replace(OLD_NEXT, NEW_NEXT, 1).replace(OLD_QUEUE, new_queue, 1)
    note = (
        "\neth_btc_30d_conditioning was scored on 2026-11-16 and is insufficient: no "
        "tercile of the ETH/BTC 30-day return has both sides of the btc_ret_30 spread in "
        "validation or test.\n"
    )
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
