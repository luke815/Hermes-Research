"""Update the backlog's first queue item now that the long metrics slice is done."""

from pathlib import Path

BACKLOG = Path("/opt/data/workspace/regime-tester/research/backlog.md")
text = BACKLOG.read_text()
old = (
    "Open interest and the long/short ratio are saved for the 13 stopped names "
    "with at most 250 daily metrics files (1,875 days, verdict 2026-11-04, every "
    "file matching the listing). DOTECOUSDT and LENDUSDT have no metrics files. "
    "What remains is the same two series for the 16 names above 250 files "
    "(12,150 daily files), liquidations (the archive publishes none), and the "
    "six-series history for the live names and for Bybit and OKX."
)
new = (
    "Open interest and the long/short ratio are saved for all 29 stopped names "
    "that have metrics files: the 13 at or under 250 daily files (1,875 days, "
    "verdict 2026-11-04) and the 16 above 250 files (12,150 days, verdict "
    "2026-11-04, results/2026-11-04_d1_binance_metrics_long.json). DOTECOUSDT and "
    "LENDUSDT have no metrics files. What remains is liquidations, which the "
    "archive does not publish, and the six-series history for the live names and "
    "for Bybit and OKX."
)
if old not in text:
    raise SystemExit("backlog sentence not found")
BACKLOG.write_text(text.replace(old, new, 1))
print("backlog updated")
