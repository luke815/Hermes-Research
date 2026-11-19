"""pair_inputs: every coin clearing the liquidity floor, for the calculator.

Reads data/panel_xs_laevitas, which the pullers already wrote. It does not pull.
A coin clears the floor when its open interest is at least 20 million dollars
on 60 days, the same floor the cross-section sweep uses. Two venues for one
coin would put the coin in the list twice, so the venue with the most days
above the floor is the one kept. BTC and ETH are always kept, from that venue.

Closes are the last 250 days of that venue, aligned to one date list so the
calculator can pair any two names. funding_7d is the mean of the last seven
funding prints, in the unit the panel stores, and funding_unit names it.
oi_usd is the last print, vol_30 is the annualized 30-day close-to-close
volatility, and sector comes from data/sectors.json where a tag exists.

Writes only dashboard/keys/pair_inputs.json. The assembler merges and pushes.
"""

import json
import math
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.panel_integrity import base_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
SECTORS = os.path.join(ROOT, "data", "sectors.json")
OUT = os.path.join(ROOT, "dashboard", "keys", "pair_inputs.json")
OI_FLOOR = 20_000_000
OI_FLOOR_DAYS = 60
WINDOW = 250
ALWAYS = ("BTC", "ETH")


def _num(value, places=6):
    """A JSON-safe number, or None when the value is missing."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return round(float(value), places)


def liquid_venues(panel):
    """One file per coin, the venue with the most days above the floor.

    A coin that never clears the floor is absent, except BTC and ETH, which
    the calculator needs as the hedge and which take the venue with the most
    days above the floor even when that count is below it.
    """
    best = {}
    for name in sorted(os.listdir(panel)):
        if not name.endswith(".csv"):
            continue
        frame = pd.read_csv(os.path.join(panel, name), usecols=lambda c: c == "oi_usd")
        if "oi_usd" not in frame.columns:
            continue
        days = int((frame["oi_usd"] >= OI_FLOOR).sum())
        coin = base_of(name.split("_", 1)[1])
        if coin not in best or days > best[coin][0]:
            best[coin] = (days, name[:-4])
    kept = {coin: file for coin, (days, file) in best.items()
            if days >= OI_FLOOR_DAYS or coin in ALWAYS}
    return kept


def _series(frame, dates):
    """Closes aligned to dates, None where the venue has no bar that day."""
    by_date = dict(zip(frame["date"], frame["close"]))
    return [_num(by_date.get(day)) for day in dates]


def _funding_7d(frame):
    window = frame["funding_rate"].dropna().tail(7) if "funding_rate" in frame else pd.Series(dtype=float)
    if window.empty:
        return None
    return _num(window.mean())


def _vol_30(frame):
    closes = frame["close"].dropna().tail(31)
    if len(closes) < 30:
        return None
    returns = closes.pct_change().dropna()
    return _num(float(returns.std()) * math.sqrt(365) * 100, 2)


def build(panel, sectors):
    """The key. as_of is the newest close date in the kept files, never typed."""
    venues = liquid_venues(panel)
    frames = {}
    last = None
    for coin, file in venues.items():
        frame = pd.read_csv(os.path.join(panel, file + ".csv"))
        frames[coin] = frame
        day = str(frame["date"].iloc[-1])
        if last is None or day > last:
            last = day
    dates = None
    for coin in ALWAYS:
        if coin in frames:
            dates = [str(d) for d in frames[coin]["date"].tail(WINDOW)]
            break
    if dates is None:
        raise SystemExit("BTC and ETH are both absent from the panel")
    names = {}
    for coin in sorted(venues):
        frame = frames[coin]
        last_row = frame.iloc[-1]
        names[coin] = {
            "close": _series(frame, dates),
            "funding_7d": _funding_7d(frame),
            "oi_usd": _num(last_row.get("oi_usd"), 0),
            "vol_30": _vol_30(frame),
            "sector": sectors.get(coin, ""),
            "venue": venues[coin].split("_", 1)[0],
        }
    return {
        "as_of": last,
        "funding_unit": "pct_8h",
        "universe_n": len(names),
        "dates": dates,
        "names": names,
    }


def main():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from dashboard_io import write_key
    from regime_tester.results_io import write_result
    sectors = json.load(open(SECTORS)) if os.path.exists(SECTORS) else {}
    payload = build(PANEL, sectors)
    write_key(OUT, payload)
    summary = {"as_of": payload["as_of"], "universe_n": payload["universe_n"],
               "dates": len(payload["dates"]), "btc": "BTC" in payload["names"],
               "eth": "ETH" in payload["names"], "funding_unit": payload["funding_unit"],
               "venues": sorted({v["venue"] for v in payload["names"].values()})}
    path = write_result("p1_pair_inputs", summary,
                        inputs=["data/panel_xs_laevitas", "data/sectors.json"])
    print(json.dumps(summary))
    print(path)


if __name__ == "__main__":
    main()
