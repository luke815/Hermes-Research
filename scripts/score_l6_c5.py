"""C5 scored again, this time through write_result.

The scoring is run_c5.run, which was pre-registered before it existed.
That script writes its own JSON and never stamps it, so the file it leaves
is not a result. This one calls the same function and stamps the payload.
It does not pull and it does not change the rule.
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regime_tester.cycle_score import clean  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
import run_c5  # noqa: E402


def verdict_of(rows):
    """The worst verdict among the rows, and the count of each."""
    counts = {}
    for row in rows:
        name = row.get("verdict") or "missing"
        counts[name] = counts.get(name, 0) + 1
    if not rows:
        return "insufficient", "no rows scored"
    if any(row.get("verdict") == "admitted" for row in rows):
        return "recorded", "a row cleared the bar; admission waits on a confirmation, which this script does not run"
    if all(row.get("verdict") == "insufficient" for row in rows):
        return "insufficient", "no row reaches the episode bar"
    return "rejected", "no row keeps a lift above 1 in validation with its neighbours"


def main():
    scored = clean(run_c5.run())
    verdict, reason = verdict_of(scored["rows"])
    payload = {
        "item": "C5",
        "today": scored["today"],
        "panel_end": scored["panel_end"],
        "candidate": scored["candidate"],
        "label": scored["label"],
        "horizon_days": scored["horizon_days"],
        "base_rates": scored["base_rates"],
        "skipped": scored["skipped"],
        "rows": scored["rows"],
        "n_rows": len(scored["rows"]),
        "verdict": verdict,
        "reason": reason,
    }
    path = write_result("l6_c5", payload, inputs=["data/raw"])
    print(path)
    print(verdict, payload["n_rows"], payload["skipped"])


if __name__ == "__main__":
    main()
