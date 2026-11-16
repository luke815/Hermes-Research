"""Pre-register btc_realized_vol_percentile_top. Writes no number and scores nothing."""

from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
LOG = ROOT / "research" / "log.md"

ENTRY = """## 2026-11-16, pre-registered before any computation: btc_realized_vol_percentile_top

Candidate: btc_realized_vol_percentile_top. Hypothesis: realized volatility at its own trailing extreme precedes tops, because blow-off moves arrive with a vol spike, and the vol factor already in the score was tested against the 10-day return, not against the top event. Rule: the factor is the 30-day standard deviation of log close-to-close returns, annualized by the square root of 365 and left unscaled, and the value used at day t is the prior bar's, so bar t itself never enters. The first 30 bars stay empty. The extreme is that value at or above its own trailing one-year percentile, the window ending at the prior bar, at the 90th percentile, with neighbours at the 85th and the 95th. A fire is an extreme reading on a top candidate day, a day within 5 percent of the trailing 60-day high. An episode counts as caught when a fire landed inside the 30 days before its start, so the hit rate and the base rate are both shares of episode starts. Horizon: 30 days. Label: the amended top event, a 20 percent drop within 30 days. Also reported, and not used to choose anything: a 15 percent drop within 20 days and a 30 percent drop within 60 days. Assets: BTC alone, and ETH as the second asset the program requires before a label is kept. Pass: at least 30 episodes in the cell across train and validation combined, lift above 1 in validation with the episode-bootstrap 90 percent interval clear of 1, the train sign agrees, and both neighbour cuts keep the sign. The test period gates admission only once it holds ten episodes. Expected independent n: about 30 to 50 episodes on BTC, which is thin, so a cell under 30 is reported as insufficient and not quoted. The top label carries the 2021 caveat from the C1 rerun, and this result carries it too.

"""


def main() -> None:
    text = LOG.read_text()
    if "btc_realized_vol_percentile_top" in text.split("## 2026-11-15", 1)[0]:
        raise SystemExit("already registered today")
    LOG.write_text(ENTRY + text)
    print("registered", LOG.stat().st_size)


if __name__ == "__main__":
    main()
