"""Record the E3 key as written, and whether the hosted page serves it.

The local key and the file on the repository's main branch are read here. The
hosted page is fetched once. A page that does not answer is recorded as such,
not described as serving the key.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, "dashboard", "data.json")
RAW = "https://raw.githubusercontent.com/luke815/Hermes-Dashboard-1/main/data.json"
PAGES = "https://luke815.github.io/Hermes-Dashboard-1/data.json"
LISTS = ("crowded_longs", "crowded_shorts", "volume_surges", "oi_builds", "oi_flushes",
         "stretched_up", "stretched_down", "new_highs", "new_lows", "squeezes")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "regime-hourly"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, None


def summary(document):
    extremes = (document or {}).get("extremes") or {}
    lists = extremes.get("lists") or {}
    return {"as_of": extremes.get("as_of"), "universe_n": extremes.get("universe_n"),
            "lists_present": sorted(name for name in LISTS if name in lists),
            "list_lengths": {name: len(lists.get(name, [])) for name in LISTS}}


def main():
    import urllib.error  # noqa: F401
    local = json.load(open(LOCAL))
    raw_status, raw = fetch(RAW)
    pages_status, pages = fetch(PAGES)
    out = {
        "item": "E3",
        "local": summary(local),
        "raw_main": {"status": raw_status, **summary(raw)},
        "pages": {"status": pages_status, **summary(pages)},
        "raw_matches_local": summary(raw)["as_of"] == summary(local)["as_of"],
        # summary sorts the names, so the comparison sorts too. Comparing
        # against LISTS as written always fails, even when every list is served.
        "pages_serves_key": pages_status == 200 and summary(pages)["lists_present"] == sorted(LISTS),
    }
    path = write_result("e3_extremes", out, inputs=["dashboard/data.json"])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
