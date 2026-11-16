"""Pre-register btc_drawdown_90_bottom. Writes no number and scores nothing."""

from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
LOG = ROOT / "research" / "log.md"

ENTRY = """## 2026-11-16, pre-registered before any computation: btc_drawdown_90_bottom

Candidate: btc_drawdown_90_bottom. Hypothesis: a deep drawdown from the 90-day high precedes a durable low, because capitulation clusters at lows, and this price-structure measure has no prior verdict. The funding-persistence cell ahead of it in the queue is not retested: the C2 rerun scored funding_streak_high_5d on the amended top label and closed it as insufficient, 3 fires in train and none in validation. Rule: the factor is the close divided by the trailing 90-day high of closes, and the value used at day t is the prior bar's, so bar t itself never enters. The extreme is that value at or below its own trailing one-year percentile, the window ending at the prior bar, at the 10th percentile, with neighbours at the 5th and the 15th. A fire is an extreme reading on a bottom candidate day, a day within 5 percent of the trailing 60-day low. An episode counts as caught when a fire landed inside the 30 days before its start, so the hit rate and the base rate are both shares of episode starts. Horizon: 30 days. Label: the amended bottom event, a 20 percent rise within 30 days with no close in between more than 7 percent below today. Also reported, and not used to choose anything: the 30 percent rise within 60 days with a 10 percent giveback. Assets: BTC alone, and ETH as the second asset the program requires before a label is kept. Pass: at least 30 episodes in the cell across train and validation combined, lift above 1 in validation with the episode-bootstrap 90 percent interval clear of 1, the train sign agrees, and both neighbour cuts keep the sign. The test period gates admission only once it holds ten episodes. Expected independent n: about 30 to 50 episodes on BTC, which is thin, so a cell under 30 is reported as insufficient and not quoted. The 2021 caveat on the top label does not apply here; the bottom label's own year share is reported.

"""


def main() -> None:
    text = LOG.read_text()
    if "btc_drawdown_90_bottom" in text.split("## 2026-11-15", 1)[0]:
        raise SystemExit("already registered today")
    LOG.write_text(ENTRY + text)
    print("registered", LOG.stat().st_size)


if __name__ == "__main__":
    main()
