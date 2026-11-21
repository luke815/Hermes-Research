"""Record the hosted-page check for the Q1 watch card.

The clause says the card reads its numbers from the scored file. This fetches
the hosted page and the hosted data file, compares the q1 key with the local
file, and writes the reading through write_result. It does not rebuild the page.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "https://luke815.github.io/Hermes-Dashboard-1/index.html"
DATA = "https://luke815.github.io/Hermes-Dashboard-1/data.json"
LOCAL = os.path.join(ROOT, "dashboard", "data.json")


def fetch(url):
    with urllib.request.urlopen(url, timeout=90) as handle:
        return handle.read()


def main():
    page = fetch(PAGE).decode()
    hosted = json.loads(fetch(DATA))
    local = json.load(open(LOCAL))
    payload = {
        "item": "Q1",
        "page_reads_q1": "d.q1" in page and "Q.windows" in page,
        "page_has_old_phrase": "weaker returns that followed high readings" in page,
        "hosted_generated_at": hosted.get("generated_at"),
        "local_generated_at": local.get("generated_at"),
        "panel_end": hosted.get("panel_end"),
        "q1_equal": hosted.get("q1") == local.get("q1"),
        "q1_source": (hosted.get("q1") or {}).get("source"),
        "q1_windows": len((hosted.get("q1") or {}).get("windows", [])),
        "q1_names": (hosted.get("q1") or {}).get("names"),
    }
    path = write_result("q1_page", payload, inputs=[
        "dashboard/data.json", "results/2026-11-21_q1_lsr_drawdown.json"])
    print(path)
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
