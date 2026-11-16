"""Pre-register eth_btc_ratio_z90_bottom. Writes no number and scores nothing."""

from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
LOG = ROOT / "research" / "log.md"

ENTRY = """## 2026-11-16, pre-registered before any computation: eth_btc_ratio_z90_bottom

Candidate: eth_btc_ratio_z90_bottom. Hypothesis: ETH weakening against BTC marks a risk-off tape, and that weakness at a BTC low should precede a bottom if the rotation story is real. The ratio's 90-day z-score is already built in regime_tester/factors.py and has no verdict against the bottom event. This is a different transform and a different target from the ETH/BTC 30-day return tercile that was insufficient on 2026-11-16. Rule: the factor is the ETH close divided by the BTC close, and its trailing 90-day z-score uses only bars before day t, so bar t itself never enters. The extreme is that z-score at or below its own trailing one-year percentile, the window ending at the prior bar, at the 10th percentile, with neighbours at the 5th and the 15th. A fire is an extreme reading on a bottom candidate day, a day within 5 percent of the trailing 60-day low. An episode counts as caught when a fire landed inside the 30 days before its start, so the hit rate and the base rate are both shares of episode starts. Horizon: 30 days. Label: the amended bottom event, a 20 percent rise within 30 days with no close in between more than 7 percent below today. Also reported, and not used to choose anything: the 30 percent rise within 60 days with a 10 percent giveback. Assets: BTC alone, and ETH as the second asset. Pass: at least 30 episodes in the cell across train and validation combined, lift above 1 in validation with the episode-bootstrap 90 percent interval clear of 1, the train sign agrees, and both neighbour cuts keep the sign. The test period gates admission only once it holds ten episodes. Expected independent n: about 30 to 50 episodes on BTC, which is thin, so a cell under 30 is reported as insufficient and not quoted. The bottom label's year share is reported.

"""


def main() -> None:
    text = LOG.read_text()
    if "eth_btc_ratio_z90_bottom" in text:
        raise SystemExit("already registered")
    LOG.write_text(ENTRY + text)
    print("registered", LOG.stat().st_size)


if __name__ == "__main__":
    main()
