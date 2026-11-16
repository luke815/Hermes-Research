"""Pre-register btc_funding_gap_bottom. Writes no number and scores nothing."""

from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
LOG = ROOT / "research" / "log.md"

ENTRY = """## 2026-11-16, pre-registered before any computation: btc_funding_gap_bottom

Candidate: btc_funding_gap_bottom. Hypothesis: BTC funding running hot against ETH funding marks leverage concentrated in BTC, and that crowding precedes a bottom in BTC rather than a top, because the positioning family already failed on the top label. This is the 7-day change of the gap, not the level, which is the transform that was rejected before. Rule: the factor is the 7-day change in the BTC funding close minus the ETH funding close, and the value ranked at day t is the prior bar's, so bar t itself never enters. The extreme is that value at or above its own trailing one-year percentile, the window ending at the prior bar, at the 90th percentile, with neighbours at the 85th and the 95th. A fire is an extreme reading on a bottom candidate day, a day within 5 percent of the trailing 60-day low. An episode counts as caught when a fire landed inside the 30 days before its start, so the hit rate and the base rate are both shares of episode starts. Horizon: 30 days. Label: the amended bottom event, a 20 percent rise within 30 days with no close in between more than 7 percent below today. Also reported, and not used to choose anything: the 30 percent rise within 60 days with a 10 percent giveback. Assets: BTC alone, and ETH as the second asset. Pass: at least 30 episodes in the cell across train and validation combined, lift above 1 in validation with the episode-bootstrap 90 percent interval clear of 1, the train sign agrees, and both neighbour cuts keep the sign. The test period gates admission only once it holds ten episodes. Expected independent n: about 30 to 50 episodes on BTC, which is thin, so a cell under 30 is reported as insufficient and not quoted. The bottom label's year share is reported.

"""


def main() -> None:
    text = LOG.read_text()
    if "btc_funding_gap_bottom" in text.split("## 2026-11-15", 1)[0]:
        raise SystemExit("already registered today")
    LOG.write_text(ENTRY + text)
    print("registered", LOG.stat().st_size)


if __name__ == "__main__":
    main()
