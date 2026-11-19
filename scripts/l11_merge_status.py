"""How many dead names the merged panel covers, read from the files.

L11's clause asks for funding, open interest and basis for the dead names
from 2021. The dead names are the span-file names whose own venue has a newer
file, which is the rule scripts/delisted_pull.py walks. A name is covered when
its panel file exists and its columns include those three. The first bar is
reported as it is: the vendor's history starts where it starts, and a name
that began trading after 2021 cannot have bars from 2021.
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
STORE = os.path.join(ROOT, "data", "laevitas", "delisted")
WANTED = ("funding_rate", "oi_usd", "basis")
VENUES = (
    ("data/binance_span.csv", "BINANCE", lambda symbol: symbol),
    ("data/bybit_span.csv", "BYBIT", lambda symbol: symbol),
    ("data/okx_span.csv", "OKX", lambda symbol: f"{symbol}-USDT-SWAP"),
)


def dead_names():
    rows = []
    for span, market, instrument_of in VENUES:
        for row in csv.DictReader(open(os.path.join(ROOT, span))):
            if row.get("last"):
                rows.append((span, market, instrument_of, row))
    newest = {}
    for span, _market, _instrument_of, row in rows:
        newest[span] = max(newest.get(span, row["last"]), row["last"])
    out = []
    for span, market, instrument_of, row in rows:
        if row["last"] < newest[span]:
            out.append({"market": market, "instrument": instrument_of(row["symbol"])})
    return out


def main():
    dead = dead_names()
    covered, no_history, missing_file = [], [], []
    for row in dead:
        saved = os.path.join(STORE, f"{row['market']}_{row['instrument']}.json")
        panel = os.path.join(PANEL, f"{row['market'].lower()}_{row['instrument']}.csv")
        if not os.path.exists(panel):
            body = json.load(open(saved)) if os.path.exists(saved) else {}
            priced = [i for i in body.get("items", []) if i.get("price") is not None]
            (no_history if not priced else missing_file).append(
                f"{row['market']}_{row['instrument']}")
            continue
        with open(panel) as handle:
            header = handle.readline().strip().split(",")
            first = handle.readline().split(",")[0]
        if not all(col in header for col in WANTED):
            missing_file.append(f"{row['market']}_{row['instrument']}")
            continue
        covered.append({"name": f"{row['market']}_{row['instrument']}", "first": first})
    firsts = sorted(row["first"] for row in covered)
    out = {
        "item": "L11",
        "dead_names": len(dead),
        "covered": len(covered),
        "no_history_from_vendor": len(no_history),
        "no_history_names": no_history,
        "missing_file": len(missing_file),
        "earliest_first_bar": firsts[0] if firsts else None,
        "latest_first_bar": firsts[-1] if firsts else None,
        "covered_before_2022": sum(1 for row in covered if row["first"] < "2022-01-01"),
        "panel_files": len([n for n in os.listdir(PANEL) if n.endswith(".csv")]),
    }
    path = write_result("l11_merge", out, inputs=["data/panel_xs_laevitas",
                                                   "data/laevitas/delisted"])
    print(json.dumps(out, indent=1))
    print(path)


if __name__ == "__main__":
    main()
