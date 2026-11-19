"""Record whether the hosted page serves the candidates key.

The local key, the file on the repository's main branch and the hosted page
are read here. A page that does not answer is recorded as such, not described
as serving the key. The done-when line is met only when the hosted page
carries cells with names and the shadow file exists.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, "dashboard", "data.json")
SHADOW = os.path.join(ROOT, "signals", "shadow.csv")
RAW = "https://raw.githubusercontent.com/luke815/Hermes-Dashboard-1/main/data.json"
PAGES = "https://luke815.github.io/Hermes-Dashboard-1/data.json"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "regime-hourly"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, None


def summary(document):
    key = (document or {}).get("candidates") or {}
    cells = key.get("cells") or []
    with_names = [cell for cell in cells if cell.get("names")]
    families = sorted({cell.get("family") for cell in cells})
    return {
        "as_of": key.get("as_of"),
        "cells": len(cells),
        "cells_with_names": len(with_names),
        "families": families,
        "all_unconfirmed": all(cell.get("status") == "unconfirmed" for cell in cells) if cells else False,
    }


def shadow_rows(path=SHADOW):
    if not os.path.exists(path):
        return 0
    return max(0, len(open(path).read().splitlines()) - 1)


def main():
    import urllib.error  # noqa: F401
    local = json.load(open(LOCAL))
    raw_status, raw = fetch(RAW)
    pages_status, pages = fetch(PAGES)
    out = {
        "item": "E4",
        "local": summary(local),
        "shadow_rows": shadow_rows(),
        "raw_main": {"status": raw_status, **summary(raw)},
        "pages": {"status": pages_status, **summary(pages)},
        "raw_matches_local": summary(raw)["as_of"] == summary(local)["as_of"],
        "pages_serves_key": (
            pages_status == 200
            and summary(pages)["cells"] > 0
            and summary(pages)["cells_with_names"] > 0
            and summary(pages)["as_of"] == summary(local)["as_of"]
        ),
    }
    path = write_result("e4_candidates", out, inputs=["dashboard/data.json", "signals/shadow.csv"])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
