"""Rebuild dashboard/data.json from the panel and raw series. No invented values.

Writes only the keys this script owns, through dashboard_io.update_keys, so the
keys other jobs own (internals, cycle, universe_rank, sweep, book) survive a
rebuild. Run only after verify_panel.py passes.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_io import update_keys  # noqa: E402

ROOT = Path("/opt/data/workspace/regime-tester")
RAW = ROOT / "data" / "raw"
PANEL = ROOT / "data" / "panel.csv"
HEAT = ROOT / "reports" / "heat_data.json"
OUT = ROOT / "dashboard" / "data.json"
LEDGER = ROOT / "research" / "ledger.csv"
HORIZON = 10
# Coinalyze returns symbols it has no friendly name for as the raw exchange code,
# e.g. HYPEUSDT_PERP.A. Those arrays stopped updating on 2026-11-05 and were
# padded with nulls back to 2020: 70 percent of the file. Only mapped tokens ship.
TOKEN = re.compile(r"[A-Z0-9]{2,10}")

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


def latest_results(suffix):
    """Newest results/<date>_<suffix>.json, by the date in the name."""
    files = sorted((ROOT / "results").glob(f"*_{suffix}.json"))
    return files[-1] if files else None


def factor_rows(heat):
    latest = latest_results("independent")
    if latest is None:
        return []
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
            "source": latest.name,
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
            "decision": (decision_of(title)
                         or decision_of(body[:600], prereg="verdict" not in title.lower())
                         or "note"),
            "what": title,
            "why": body[:600],
        })
    return list(reversed(rows[-30:]))


VERDICTS = {
    "admitted": r"\badmit(?:s|ted)?\b",
    "rejected": r"\breject(?:s|ed)?\b|\bclosed\b",
    "insufficient": r"\binsufficient\b",
    "void": r"\bvoid(?:ed)?\b",
}
NEGATED = re.compile(r"\b(?:nothing (?:is|was) |not |no |never |none (?:is|was) )(?=admit|reject|insufficient|void)")
OPS = re.compile(r"refresh|heartbeat|backfill|\bpull\b|daemon|row count|hourly")


def decision_of(text, prereg=True):
    """The first verdict word in a log entry, or None. Negated words ("nothing is admitted") don't count."""
    lower = text.lower()
    if prereg and re.search(r"pre-?regist", lower[:120]):
        return "prereg"
    lower = NEGATED.sub("NEG ", lower)
    hits = [(m.start(), name) for name, pattern in VERDICTS.items()
            for m in [re.search(pattern, lower)] if m and lower[max(0, m.start() - 4):m.start()] != "NEG "]
    if hits:
        return min(hits)[1]
    if OPS.search(lower[:120]):
        return "ops"
    return None


def backlog_rows():
    """Every open item from the top of backlog.md down to the completed list.

    The agent works top-down, and the items it takes next (X1, P1, L-items, the
    audit's A-block) sit above "## Queue", so reading only that section hid them.
    Items are "- X1. text" bullets or "4. text" lines; a repeated id keeps its
    first, highest occurrence.
    """
    text = (ROOT / "research" / "backlog.md").read_text()
    stop = min([i for i in (text.find("\nCompleted,"), text.find("\n## Pass rules")) if i >= 0] or [len(text)])
    rows, seen, section = [], set(), ""
    for line in text[:stop].splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        bullet = re.match(r"^- ([A-Z]{1,3}\d{1,3}[a-z]?)\.\s+(.*)", line)
        numbered = re.match(r"^(\d{1,3})\.\s+(.*)", line)
        if not (bullet or numbered):
            continue
        item = backlog_item(f"{bullet.group(1)}. {bullet.group(2)}" if bullet else numbered.group(2),
                            numbered.group(1) if numbered else len(rows) + 1)
        if numbered and item["id"] == numbered.group(1):
            # a plain numbered line; prefix the section so "Queue 4" and "Next ten 4" differ
            item["id"] = f"{section[:1]}{numbered.group(1)}" if section else numbered.group(1)
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        item["section"] = section
        rows.append(item)
    return rows


def backlog_item(text, position):
    """The page reads id, title, status. The backlog line is free text, so parse it.

    Status comes only from an explicit "Verdict <date>: <word>" phrase, never from
    a verdict word used in passing ("the admitted momentum factor").
    """
    head = re.match(r"([A-Z]{1,3}\d{1,3}[a-z]?)\b[,.:]?\s*(.*)", text)
    item_id, rest = (head.group(1), head.group(2)) if head else (str(position), text)
    sentences = re.split(r"(?<=[.!?])\s", rest)
    title = sentences[0]
    if len(title) < 25 and len(sentences) > 1:
        title = title + " " + sentences[1]
    lower = text.lower()
    said = re.search(r"verdict(?:\s+\d{4}-\d{2}-\d{2})?\s*:\s*([a-z]+)", lower)
    if said:
        word = said.group(1)
        status = word if word in ("admitted", "rejected", "insufficient", "void") else "done"
    elif re.search(r"\bdone(?:\s+20\d\d-\d\d-\d\d)?\s*:", lower):
        status = "done"
    elif re.search(r"not yet scored|pre-?registered", lower):
        status = "prereg"
    elif re.search(r"\bblocked\b|\bon hold\b", lower):
        status = "blocked"
    else:
        status = "queued"
    return {"id": item_id, "title": title[:200], "status": status, "verdict": text[:600]}


HOLDOUT_PASSED = False

# name, series key, unit, decimals, what it reads as
DERIVATIVES = {
    "BTC": [
        ("DVOL", "dvol_btc", "vol pts", 1, "Deribit 30-day implied vol index"),
        ("ATM implied vol", "atm_iv_btc", "vol pts", 1, "mean across tenors"),
        ("Realized vol", "rv_btc", "vol pts", 1, "mean across windows"),
        ("Implied minus realized", "vrp_btc", "vol pts", 1, "positive: options price more movement than is happening"),
        ("Skew", "skew_btc", "vol pts", 1, "Laevitas skew, mean across tenors"),
        ("25d risk reversal", "rr_btc", "vol pts", 1, "calls minus puts; negative means puts bid"),
        ("Basis, annualized", "basis_btc", "%", 2, "futures over spot, mean across tenors"),
        ("Funding, Binance", "btc_funding", "% / 8h", 4, "daily close of the perp funding rate"),
        ("Funding, OI-weighted", "oiw_funding_btc", "% / 8h", 4, "cross-venue"),
    ],
    "ETH": [
        ("DVOL", "dvol_eth", "vol pts", 1, "Deribit 30-day implied vol index"),
        ("ATM implied vol", "atm_iv_eth", "vol pts", 1, "mean across tenors, history from 2025-10"),
        ("Realized vol", "rv_eth", "vol pts", 1, "history from 2024-10"),
        ("Implied minus realized", "vrp_eth", "vol pts", 1, "positive: options price more movement than is happening"),
        ("Skew", "skew_eth", "vol pts", 1, "Laevitas skew, mean across tenors"),
        ("25d risk reversal", "rr_eth", "vol pts", 1, "calls minus puts; negative means puts bid"),
        ("Basis, annualized", "basis_eth", "%", 2, "futures over spot, mean across tenors"),
        ("Funding, Binance", "eth_funding", "% / 8h", 4, "daily close of the perp funding rate"),
        ("Funding, OI-weighted", "oiw_funding_eth", "% / 8h", 4, "cross-venue"),
    ],
}


def reading(values, dates, window=365):
    """Latest value, 1d and 7d change, percentile in the trailing year, last 30 points."""
    points = [(d, v) for d, v in zip(dates, values) if v is not None]
    if not points:
        return None
    last_day, last = points[-1]
    by_day = dict(points)

    def back(days):
        day = (pd.Timestamp(last_day) - pd.Timedelta(days=days)).date().isoformat()
        prior = by_day.get(day)
        return None if prior is None else last - prior

    year_start = (pd.Timestamp(last_day) - pd.Timedelta(days=window)).date().isoformat()
    year = [v for d, v in points if d > year_start]
    return {
        "value": last,
        "as_of": last_day,
        "chg_1d": back(1),
        "chg_7d": back(7),
        "pct_1y": sum(1 for v in year if v <= last) / len(year) if len(year) >= 60 else None,
        "spark": [v for _, v in points[-30:]],
    }


def derivatives_block(series, dates):
    vrp = {}
    for asset in ("btc", "eth"):
        iv, rv = series.get(f"dvol_{asset}"), series.get(f"rv_{asset}")
        if iv and rv:
            vrp[f"vrp_{asset}"] = [None if a is None or b is None else a - b for a, b in zip(iv, rv)]
    assets = {}
    for asset, rows in DERIVATIVES.items():
        out = []
        for name, key, unit, places, note in rows:
            values = series.get(key) if key in series else vrp.get(key)
            got = reading(values, dates) if values else None
            if not got:
                continue
            got = {k: (round(v, places + 2) if isinstance(v, float) else v) for k, v in got.items()}
            got["spark"] = [round(v, places + 2) for v in got["spark"]]
            out.append({"name": name, "key": key, "unit": unit, "decimals": places, "note": note, **got})
        assets[asset] = out
    return {"as_of": dates[-1], "assets": assets,
            "note": "Readings, not signals. None of these has passed the holdout as a predictor."}


def score_ledger(rows, dates, btc, horizon=HORIZON):
    """Each forecast scored against the BTC return over the NEXT horizon days.

    ledger.csv's realized_10d column held the trailing 10-day return, so the
    page compared each forecast with the move that had already happened. Here
    the forward return is taken from the price series itself, and it stays null
    until the horizon has passed.
    """
    index = {day: i for i, day in enumerate(dates)}
    out = []
    for row in rows:
        day = row["date"]
        forecast = num(row.get("forecast_10d"))
        i = index.get(day)
        realized = None
        if i is not None and i + horizon < len(btc) and btc[i] and btc[i + horizon]:
            realized = (btc[i + horizon] / btc[i] - 1) * 100
        hit = None
        if realized is not None and forecast is not None and forecast != 0:
            hit = (forecast > 0) == (realized > 0)
        out.append({
            "date": day,
            "heat": round_or_none(row.get("heat"), 4),
            "forecast": None if forecast is None else round(forecast * 100, 4),
            "realized": round_or_none(realized, 4),
            "matures": None if i is None else (pd.Timestamp(day) + pd.Timedelta(days=horizon)).date().isoformat(),
            "hit": hit,
        })
    return out


def job_line(now, panel_end):
    """Status from the panel's actual age, not a hard-coded 'OK age=1d'."""
    age = (datetime.fromisoformat(now[:10]) - datetime.fromisoformat(panel_end)).days
    status = "OK" if age <= 2 else "STALE"
    return {
        "name": "regime-daily-refresh",
        "last_run": now,
        "status": status,
        "age_days": age,
        "line": f"STATUS {status} regime-daily-refresh panel_end={panel_end} age={age}d",
    }


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
    price = coinalyze("coinalyze_ohlcv-history.json", "c")
    funding = coinalyze("coinalyze_funding-rate-history.json", "c")
    oi = coinalyze("coinalyze_open-interest-history.json", "c")
    liq = coinalyze("coinalyze_liquidation-history.json", "l")
    lsr = coinalyze("coinalyze_long-short-ratio-history.json", "r")

    series = {"date": dates}
    def named(frames):
        return {t: m for t, m in frames.items() if TOKEN.fullmatch(t)}

    for token, mapping in named(price).items():
        key = "btc" if token == "BTC" else "eth" if token == "ETH" else f"price_{token}"
        series[key] = [round_or_none(v, 4) for v in align(dates, mapping)]
    for token, mapping in named(funding).items():
        if f"{token.lower()}_funding" in panel.columns:
            continue  # btc_funding and eth_funding come from the panel, same values
        series[f"funding_{token}"] = [round_or_none(v, 6) for v in align(dates, mapping)]
    for token, mapping in named(oi).items():
        series[f"oi_{token}"] = [round_or_none(v, 0) for v in align(dates, mapping)]
    for token, mapping in named(liq).items():
        series[f"liq_{token}"] = [round_or_none(v, 0) for v in align(dates, mapping)]
    for token, mapping in named(lsr).items():
        series[f"lsr_{token}"] = [round_or_none(v, 4) for v in align(dates, mapping)]

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
        ledger_rows = score_ledger(
            [{"date": str(r["date"])[:10], "heat": r.get("heat"), "forecast_10d": r.get("forecast_10d")}
             for _, r in frame.iterrows()],
            dates, series["btc"])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    zone = "hot" if heat_now is not None and heat_now >= 0.4 else "cold" if heat_now is not None and heat_now <= -0.4 else "middle"
    payload = {
        "generated_at": now,
        "panel_end": last,
        "regime": {
            "score": round(heat_now, 2) if heat_now is not None else None,
            "hot": 0.4,
            "cold": -0.4,
            "label": "Momentum and volatility, four factors",
            "change_7d": None if heat_now is None or heat_week is None else round(heat_now - heat_week, 4),
            "zone": zone,
            "validated": False,
            "note": ("Context, not a signal. The four-factor score and its hot zone failed the "
                     "three-period holdout (log.md, 2026-10-29 to 11-01): t 1.39 on BTC, n=25, "
                     "and the hot-zone mean rests on 2020 and 2024."),
        },
        "forecast": {
            "btc_10d": forecast_now,
            # Reliable needs both an elevated zone and a holdout that passed. The
            # holdout failed, so this stays false until a results file says otherwise.
            "reliable": bool(zone == "hot" and HOLDOUT_PASSED),
            "zone_hit_rate": None,
            "zone_n": None,
            "note": "Rolling two-year regression of BTC 10-day return on the four factors. Not validated out of sample.",
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
        "jobs": [job_line(now, last)],
    }
    update_keys(OUT, payload, stamp=now)
    print(f"wrote {OUT} bytes {OUT.stat().st_size} panel_end {last} series {len(series) - 1} dates {length}")


if __name__ == "__main__":
    main()
