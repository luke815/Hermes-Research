"""Count vendor files whose price field jumps while the index does not.

The panel builder copies the vendor price field into close. On 1000PEPE
that field jumps by about a thousand for one day while the index beside it
stays put, and the panel copies the jump. This walks the perpetual store
already on disk and writes the count. It does not pull and does not rewrite
the panel.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "perpetuals")
JUMP = 50


def jumps_in(items, jump=JUMP):
    """Days whose price jumps by jump while the index beside it does not."""
    rows = []
    for item in items:
        price, index = item.get("price"), item.get("index")
        if not price or not index or "date" not in item:
            continue
        day = datetime.fromtimestamp(
            item["date"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        rows.append((day, price, index))
    rows.sort()
    found = []
    for (day, price, index), (prev_day, prev_price, prev_index) in zip(
            rows[1:], rows):
        price_moved = prev_price and (
            price / prev_price >= jump or prev_price / price >= jump)
        index_held = prev_index and (1 / jump) < (index / prev_index) < jump
        if price_moved and index_held:
            found.append({
                "date": day, "price": price, "prior_price": prev_price,
                "index": index, "prior_index": prev_index})
    return found


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    files = 0
    no_index = 0
    affected = []
    jump_days = 0
    for name in sorted(os.listdir(STORE)):
        if not name.endswith(".json"):
            continue
        files += 1
        body = json.loads(open(os.path.join(STORE, name)).read())
        found = jumps_in(body.get("items", []))
        if not found and not any(
                item.get("index") for item in body.get("items", [])):
            no_index += 1
        if found:
            affected.append({"file": name, "jumps": len(found),
                             "first": found[0]["date"]})
            jump_days += len(found)
            print(f"{name} {len(found)} first {found[0]['date']}", flush=True)
    payload = {
        "item": "A7",
        "today": today,
        "store": "data/laevitas/perpetuals",
        "files": files,
        "files_without_index": no_index,
        "files_with_price_jump": len(affected),
        "jump_days": jump_days,
        "jump": JUMP,
        "affected": affected,
    }
    path = write_result("a7_price_jumps", payload, inputs=[
        "data/laevitas/perpetuals"])
    print(path)
    print(json.dumps({k: payload[k] for k in (
        "files", "files_without_index", "files_with_price_jump",
        "jump_days")}))


if __name__ == "__main__":
    main()
