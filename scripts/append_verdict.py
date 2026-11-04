"""Append the verdict for the long-metrics slice to the research log.

Anchors on the candidate heading so an earlier entry with the same closing
sentence is not touched.
"""

from pathlib import Path

LOG = Path("/opt/data/workspace/regime-tester/research/log.md")
text = LOG.read_text()
heading = "## 2026-11-04, pre-registered before any computation: D1 Binance open interest and long/short for the long stopped names"
start = text.index(heading)
end = text.index("\n", text.index("Expected independent n: not applicable, no return is scored.", start))
verdict = (
    "\n\nVerdict: recorded, not admitted. The 16 names above 250 daily files are saved, "
    "12,150 days, and no checksum failed. Open interest is present on every saved day. "
    "1,106 days have a blank long/short or taker ratio, the same empty field the archive "
    "published for the short names. Fifteen of the 16 match the listing on first date, "
    "last date and day count. MATICUSDT does not: its listing starts at a file named "
    "1993.zip, which carries 2023-12-18 and duplicates the dated file for that day, so "
    "the saved file has 1,038 days against 1,039 zips. SRMUSDT has one file, dated "
    "2023-01-17, whose rows also cover 2023-01-18, so the saved file has 378 days against "
    "377 zips. Both were re-read from the archive and the saved dates equal the dates "
    "inside the files. A third name, BDXNUSDT, was re-read the same way and matched "
    "exactly. 5,167 price days have no metrics day and 718 metrics days have no price "
    "day, so the archive does not treat the last trade as the last metrics observation. "
    "Liquidations are not in the archive, and Bybit, OKX and the live names were not "
    "pulled. results/2026-11-04_d1_binance_metrics_long.json. The score is unchanged. "
    "Nine tests since the last admission.\n"
)
if "d1_binance_metrics_long.json" in text:
    raise SystemExit("verdict already present")
LOG.write_text(text[:end] + verdict + text[end:])
print("appended at", end)
