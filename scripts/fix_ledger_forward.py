"""Rewrite the ledger's realized_10d from the forward return.

The column held the trailing 10-day BTC return, so every row scored a forecast
against the move that had already happened, including rows whose horizon has
not elapsed. The forward return is price[t+10] / price[t] - 1, and a row stays
blank until that day exists in the panel. Idempotent: running it twice writes
the same file.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
PANEL = ROOT / "data" / "panel.csv"
LEDGER = ROOT / "research" / "ledger.csv"
HORIZON = 10


def prices():
    out = {}
    with PANEL.open() as fh:
        for row in csv.DictReader(fh):
            day = next(iter(row.values()))[:10]
            out[day] = float(row["btc_price"])
    return out


def forward(px, day):
    later = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=HORIZON)).strftime("%Y-%m-%d")
    if day in px and later in px and px[day]:
        return px[later] / px[day] - 1
    return None


def rewrite():
    px = prices()
    with LEDGER.open() as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys()) if rows else []
    matured = 0
    for row in rows:
        realized = forward(px, row["date"])
        if realized is None:
            row["realized_10d"] = ""
            row["direction_right"] = ""
            continue
        row["realized_10d"] = f"{realized:.5f}"
        forecast = row["prior_forecast"]
        row["direction_right"] = (
            "yes" if (float(forecast) >= 0) == (realized >= 0) else "no") if forecast else ""
        matured += 1
    tmp = LEDGER.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as fh:
        out = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        out.writeheader()
        out.writerows(rows)
    tmp.replace(LEDGER)
    return {"rows": len(rows), "matured": matured, "blank": len(rows) - matured}


if __name__ == "__main__":
    print(rewrite())
