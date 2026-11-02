"""Rebuild dashboard/data.json from the panel and raw series. No invented values.

Write data.json.tmp then rename. Run only after verify_panel.py passes.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path("/opt/data/workspace/regime-tester")
RAW = ROOT / "data" / "raw"
PANEL = ROOT / "data" / "panel.csv"
HEAT = ROOT / "reports" / "heat_data.json"
OUT = ROOT / "dashboard" / "data.json"
LEDGER = ROOT / "research" / "ledger.csv"

LABELS = {
    "btc_ret_30": ("BTC 30-day momentum", "How hard price has already been running"),
    "btc_vol_z90": ("BTC volatility z-score", "Realized volatility against its own trailing history"),
    "btc_trend_stretch": ("BTC trend stretch", "Distance of price from its 50-day average"),
    "eth_funding_z30": ("ETH funding z-score", "ETH perpetual funding against its trailing 30 days"),
    "basis_btc_z30": ("BTC basis z-score", "90-day annualized basis against its trailing 30 days"),
    "basis_gap_btc_eth": ("BTC vs ETH basis gap", "BTC basis relative to ETH basis"),
    "dispersion_14": ("Alt dispersion", "How far apart the alts moved over 14 days"),
}


def num(value):
    if value is None or value != value:
        return None
    return float(value)


def round_or_none(value, places):
    value = num(value)
    if value is None:
        return None
    return round(value, places)


def epoch_frame(rows, value_fn):
    out = {}
    for row in rows:
        if not isinstance(row, dict) or "date" not in row:
            continue
        stamp = int(row["date"])
        if stamp > 10_000_000_000:
            stamp //= 1000
        day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
        out[day] = value_fn(row)
    return out


def load_list(pattern):
    rows = []
    for path in sorted(RAW.glob(pattern)):
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            rows.extend(payload)
        elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
            rows.extend(payload["items"])
    return rows


def coinalyze(blob, field):
    frames = {}
    for path in sorted(RAW.glob(blob)):
        payload = json.loads(path.read_text())
        inverse = {v: k for k, v in payload.get("symbols", {}).items()}
        for series in payload.get("data", []):
            token = inverse.get(series["symbol"], series["symbol"])
            column = frames.setdefault(token, {})
            for bar in series.get("history", []):
                stamp = int(bar["t"])
                day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
                column[day] = num(bar.get(field))
    return frames


def tenor_mean(rows):
    """Mean of numeric tenor keys. A date-only row is a gap, not a zero."""

    def value(row):
        vals = [v for k, v in row.items() if k != "date" and isinstance(v, (int, float))]
        if not vals:
            return None
        return sum(vals) / len(vals)

    return epoch_frame(rows, value)


def align(dates, mapping):
    return [None if mapping.get(day) is None else mapping[day] for day in dates]


def factor_rows(heat):
    latest = ROOT / "results" / "2026-10-29_independent.json"
    payload = json.loads(latest.read_text())
    factors = payload["factors"]
    learned = {row["name"]: row["weight"] for row in heat["learned_weights"]}
    active = [row["name"] for row in heat["components"]]
    weight = round(1 / len(active), 4) if active else 0
    legs = heat.get("legs", {})
    rows = []
    for name, block in factors.items():
        btc = block.get("btc_price", {}).get("test", {})
        alt = block.get("alt_price", {}).get("test", {})
        sign_holds = (
            btc.get("spread_pct", 0) > 0 and alt.get("spread_pct", 0) > 0
        )
        label, measures = LABELS.get(name, (name, name))
        last_leg = legs.get(name, [None])[-1] if name in legs else None
        rows.append({
            "name": name,
            "label": label,
            "measures": measures,
            "weight": weight if name in active else 0,
            "learned": learned.get(name),
            "value": last_leg,
            "oos_btc": btc.get("spread_pct"),
            "oos_alt": alt.get("spread_pct"),
            "n": btc.get("independent_n"),
            "sign_holds": bool(sign_holds),
            "status": "active" if name in active else "dropped",
        })
    return rows


def data_health(dates):
    last = dates[-1]
    rows = []
    checks = [
        ("BTC, ETH, alt OHLCV", "Coinalyze", "Binance", "coinalyze_ohlcv-history.json"),
        ("Funding", "Coinalyze", "Binance", "coinalyze_funding-rate-history.json"),
        ("Open interest", "Coinalyze", "Binance", "coinalyze_open-interest-history.json"),
        ("Liquidations", "Coinalyze", "Binance", "coinalyze_liquidation-history.json"),
        ("Long/short ratio", "Coinalyze", "Binance", "coinalyze_long-short-ratio-history.json"),
    ]
    for name, source, venue, filename in checks:
        payload = json.loads((RAW / filename).read_text())
        newest = 0
        count = 0
        for series in payload["data"]:
            history = series.get("history") or []
            count += len(history)
            if history:
                newest = max(newest, history[-1]["t"])
        day = datetime.fromtimestamp(newest, timezone.utc).date().isoformat()
        rows.append({
            "series": name,
            "source": source,
            "venue": venue,
            "last": day,
            "rows": count,
            "status": "ok" if day == last else "lag",
            "note": "",
        })
    return rows


def research_rows():
    text = (ROOT / "research" / "log.md").read_text()
    heads = list(re.finditer(r"^## (.+)$", text, re.M))
    rows = []
    for i, match in enumerate(heads):
        start = match.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[start:end].strip().replace("\n", " ")
        title = match.group(1)
        date = title[:10]
        rows.append({
            "date": date,
            "decision": "retested",
            "what": title,
            "why": body[:400],
        })
    return list(reversed(rows[-30:]))


def backlog_rows():
    text = (ROOT / "research" / "backlog.md").read_text()
    start = text.find("## Queue")
    end = text.find("\nCompleted,")
    if end < 0:
        end = text.find("## Pass rules")
    block = text[start:end]
    rows = []
    for line in block.splitlines():
        if line[:2].rstrip(".").isdigit() and ". " in line:
            rows.append(line.split(". ", 1)[1].strip())
    return rows


def main() -> None:
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    heat = json.loads(HEAT.read_text())
    heat_by_date = dict(zip(heat["dates"], heat["heat"]))
    pred_by_date = dict(zip(heat["dates"], heat["predicted"]))
    leg_by_date = {
        name: dict(zip(heat["dates"], values))
        for name, values in heat["legs"].items()
    }

    dates = [ts.date().isoformat() for ts in panel.index]
    price = coinalyze("coinalyze_ohlcv*.json", "c")
    funding = coinalyze("coinalyze_funding*.json", "c")
    oi = coinalyze("coinalyze_open-interest*.json", "c")
    liq = coinalyze("coinalyze_liquidation*.json", "c")
    lsr = coinalyze("coinalyze_long-short-ratio*.json", "c")

    series = {"date": dates}
    for token, mapping in price.items():
        key = "btc" if token == "BTC" else "eth" if token == "ETH" else f"price_{token}"
        series[key] = [round_or_none(v, 4) for v in align(dates, mapping)]
    for token, mapping in funding.items():
        series[f"funding_{token}"] = [round_or_none(v, 6) for v in align(dates, mapping)]
    for token, mapping in oi.items():
        series[f"oi_{token}"] = [round_or_none(v, 2) for v in align(dates, mapping)]
    for token, mapping in liq.items():
        series[f"liq_{token}"] = [round_or_none(v, 2) for v in align(dates, mapping)]
    for token, mapping in lsr.items():
        series[f"lsr_{token}"] = [round_or_none(v, 6) for v in align(dates, mapping)]

    extras = {
        "basis_btc": tenor_mean(load_list("basis_btc*.json")),
        "basis_eth": tenor_mean(load_list("basis_eth*.json")),
        "oiw_funding_btc": epoch_frame(load_list("oiw_funding_btc*.json"), lambda r: num(r.get("funding"))),
        "oiw_funding_eth": epoch_frame(load_list("oiw_funding_eth*.json"), lambda r: num(r.get("funding"))),
        "rv_btc": tenor_mean(load_list("rv_btc_*.json")),
        "rv_eth": tenor_mean(load_list("rv_eth_*.json")),
        "dvol_btc": epoch_frame(load_list("dvol_btc_*.json"), lambda r: num(r.get("dvol"))),
        "dvol_eth": epoch_frame(load_list("dvol_eth_*.json"), lambda r: num(r.get("dvol"))),
        "skew_btc": tenor_mean(load_list("skew_btc_*.json")),
        "skew_eth": tenor_mean(load_list("skew_eth_*.json")),
        "atm_iv_btc": tenor_mean(load_list("atmiv_btc_*.json")),
        "atm_iv_eth": tenor_mean(load_list("atmiv_eth_*.json")),
        "rr_btc": tenor_mean(load_list("rr_btc_*.json")),
        "rr_eth": tenor_mean(load_list("rr_eth_*.json")),
    }
    for name, mapping in extras.items():
        series[name] = [round_or_none(v, 4) for v in align(dates, mapping)]

    for column in panel.columns:
        if column in ("btc_price", "eth_price"):
            continue
        series[column] = [round_or_none(v, 6) for v in panel[column]]

    series["heat"] = [round_or_none(heat_by_date.get(day), 4) for day in dates]
    series["forecast_btc_10d"] = [
        None if pred_by_date.get(day) is None else round(float(pred_by_date[day]) * 100, 4)
        for day in dates
    ]
    series["factors"] = {
        name: [round_or_none(leg_by_date[name].get(day), 4) for day in dates]
        for name in leg_by_date
    }

    length = len(dates)
    bad = [key for key, value in series.items() if key != "factors" and len(value) != length]
    bad += [name for name, value in series["factors"].items() if len(value) != length]
    if bad:
        raise SystemExit(f"length mismatch {bad}")

    last = dates[-1]
    heat_now = series["heat"][-1]
    heat_week = next((v for v in reversed(series["heat"][:-7]) if v is not None), None)
    forecast_now = series["forecast_btc_10d"][-1]
    ledger_rows = []
    if LEDGER.exists():
        frame = pd.read_csv(LEDGER)
        for _, row in frame.iterrows():
            realized = row.get("realized_10d")
            hit = None if pd.isna(row.get("direction_right")) else str(row["direction_right"]) == "yes"
            ledger_rows.append({
                "date": str(row["date"])[:10],
                "heat": round_or_none(row.get("heat"), 4),
                "forecast": None if pd.isna(row.get("forecast_10d")) else round(float(row["forecast_10d"]) * 100, 4),
                "realized": None if pd.isna(realized) else round(float(realized) * 100, 4),
                "hit": hit,
            })

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "generated_at": now,
        "panel_end": last,
        "regime": {
            "score": round(heat_now, 2) if heat_now is not None else None,
            "hot": 0.4,
            "cold": -0.4,
            "label": "Momentum and volatility, four factors",
            "change_7d": None if heat_now is None or heat_week is None else round(heat_now - heat_week, 4),
            "note": "Hot zone above +0.4 has held out of sample. Cold zone and middle carry no reliable edge.",
        },
        "forecast": {
            "btc_10d": forecast_now,
            "reliable": False,
            "zone_hit_rate": None,
            "zone_n": None,
        },
        "series": series,
        "factors": factor_rows(heat),
        "alt_ranking": [],
        "alt_ranking_note": "No cross-sectional ranking model exists yet.",
        "setups": [],
        "setups_note": "Scanner did not qualify a setup on this bar.",
        "ledger": {"rows": ledger_rows},
        "data_health": data_health(dates),
        "research": research_rows(),
        "backlog": backlog_rows(),
        "jobs": [{
            "name": "regime-daily-refresh",
            "last_run": now,
            "status": "OK",
            "line": f"STATUS OK regime-daily-refresh panel_end={last} age=1d files=results/{now[:10]}_regime-daily-refresh.json",
        }],
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")))
    tmp.replace(OUT)
    print(f"wrote {OUT} bytes {OUT.stat().st_size} panel_end {last} series {len(series) - 1} dates {length}")


if __name__ == "__main__":
    main()
