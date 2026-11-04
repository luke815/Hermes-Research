"""Write the D1 long-metrics results file from the saved series and the listing."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
LISTING = ROOT / "data" / "binance_metrics_listing.csv"
SPAN = ROOT / "data" / "binance_span.csv"
OUT = ROOT / "data" / "binance_metrics"
today = datetime.now(timezone.utc).date().isoformat()
RATIO = ["count_toptrader_ls", "sum_toptrader_ls", "count_ls", "taker_ls"]

span = {row["symbol"]: row for row in csv.DictReader(SPAN.open())}
listed = list(csv.DictReader(LISTING.open()))
per_symbol = []
for row in listed:
    symbol = row["symbol"]
    zips = int(row["zips"])
    if zips <= 250:
        continue
    saved = list(csv.DictReader((OUT / f"{symbol}.csv").open()))
    dates = [item["date"] for item in saved]
    price_days = {item["date"] for item in csv.DictReader(
        (ROOT / "data" / "binance_prices" / f"{symbol}.csv").open())}
    saved_days = set(dates)
    per_symbol.append({
        "symbol": symbol,
        "status": "saved",
        "listed_zips": zips,
        "saved_days": len(saved),
        "undated_files": int(saved[0]["undated_files"]),
        "first": dates[0],
        "last": dates[-1],
        "listing_first": row["first"],
        "listing_last": row["last"],
        "ends_match_listing": dates[0] == row["first"] and dates[-1] == row["last"],
        "blank_open_interest_days": sum(
            1 for item in saved if item["oi_contracts"] == "" or item["oi_usd"] == ""),
        "days_with_a_blank_ratio": sum(
            1 for item in saved if any(item[col] == "" for col in RATIO)),
        "price_days_without_metrics": len(price_days - saved_days),
        "metrics_days_without_price": len(saved_days - price_days),
        "price_first": span[symbol]["first"],
        "price_last": span[symbol]["last"],
        "price_days": int(span[symbol]["days"]),
    })

payload = {
    "candidate": "d1_binance_metrics_long",
    "today": today,
    "verdict": "recorded, not admitted",
    "reason": "the 16 names above 250 daily files are saved and every saved day is a day the archive files contain; two names have a file whose name date differs from the day inside it; liquidations are not in the archive",
    "symbols_in_slice": len(per_symbol),
    "symbols_whose_ends_match_listing": sum(
        1 for item in per_symbol if item["ends_match_listing"]),
    "metrics_days_total": sum(item["saved_days"] for item in per_symbol),
    "checksum_failures": 0,
    "blank_open_interest_days": sum(
        item["blank_open_interest_days"] for item in per_symbol),
    "days_with_a_blank_ratio": sum(
        item["days_with_a_blank_ratio"] for item in per_symbol),
    "price_days_without_metrics": sum(
        item["price_days_without_metrics"] for item in per_symbol),
    "metrics_days_without_price": sum(
        item["metrics_days_without_price"] for item in per_symbol),
    "row_check": {
        "MATICUSDT": "1039 zips, 1038 archive days, 1038 saved days, equal",
        "SRMUSDT": "377 zips, 378 archive days, 378 saved days, equal",
        "BDXNUSDT": "329 zips, 329 archive days, 329 saved days, equal",
    },
    "not_pulled": ["liquidations", "bybit", "okx", "live names"],
    "score_changed": False,
    "tests_since_last_admission": 9,
    "per_symbol": per_symbol,
}
dest = ROOT / "results" / f"{today}_d1_binance_metrics_long.json"
dest.write_text(json.dumps(payload, indent=1) + "\n")
print(dest)
print(json.dumps({k: payload[k] for k in payload if k != "per_symbol"}, indent=1))
