"""Renumber the next-ten list after the realized-vol item was removed.

No numbers from a result are written here.
"""

from pathlib import Path

BACKLOG = Path("/opt/data/workspace/regime-tester/research/backlog.md")

OLD = (
    "3. Funding 7-day average and open-interest 7-day change as cross-sectional signals.\n"
    "4. One-day reversal in the bottom half of the universe by open interest.\n"
    "5. eth_btc_30d_conditioning. The btc_ret_30 spread split by tercile of the ETH/BTC "
    "30-day return. Expected n about 20 per cell, so report it as thin.\n"
    "6. BTC 1-day and 3-day horizons for the four live factors, non-overlapping, net of "
    "costs, both halves, BTC and the alt basket. Not yet scored at those horizons.\n"
)
NEW = (
    "2. Funding 7-day average and open-interest 7-day change as cross-sectional signals.\n"
    "3. One-day reversal in the bottom half of the universe by open interest.\n"
    "4. eth_btc_30d_conditioning. The btc_ret_30 spread split by tercile of the ETH/BTC "
    "30-day return. Expected n about 20 per cell, so report it as thin.\n"
    "5. BTC 1-day and 3-day horizons for the four live factors, non-overlapping, net of "
    "costs, both halves, BTC and the alt basket. Not yet scored at those horizons.\n"
)


def main() -> None:
    text = BACKLOG.read_text()
    if OLD not in text:
        raise SystemExit("numbering block missing")
    BACKLOG.write_text(text.replace(OLD, NEW, 1))
    print("renumbered", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
