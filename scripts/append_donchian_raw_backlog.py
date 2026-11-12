"""Append this confirmation to the backlog sentence."""

from pathlib import Path

path = Path("research/backlog.md")
text = path.read_text()
needle = "results/2026-11-12_confirm_kst.json."
addition = (
    " Fifty-second attempt 2026-11-12: donchian_width|raw|below|20|ret_1|btc|none|daily "
    "rejected. Validation t-stat 1.2406 against bar 2.9771, independent n 167, "
    "sign flipped. Test spread 0.3595 percent, t-stat 1.7316, independent n 93, "
    "sign flipped. Closed. results/2026-11-12_confirm_donchian_raw.json."
)
if text.count(needle) != 1:
    raise SystemExit("needle count " + str(text.count(needle)))
path.write_text(text.replace(needle, needle + addition, 1))
print("updated", path.stat().st_size)
