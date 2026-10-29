"""Load Laevitas exports (CSV or API JSON) into one panel per token.

A panel has a UTC datetime index, a `price` column, and one column per
indicator. Files are matched to a token by an explicit currency column, a
token column, or the filename stem.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

TIMESTAMP_COLS = ("date", "timestamp", "time", "ts", "datetime")
PRICE_COLS = ("price", "close", "index_price", "index", "underlying", "mark_price")
TOKEN_COLS = ("currency", "token", "asset", "symbol", "underlying")

# Filename stems that are a metric, not a token. Longest first so
# "funding_apr" wins over "funding".
METRIC_TOKENS = (
    "funding_apr", "funding", "open_interest", "oi", "basis", "yield",
    "atm_iv", "iv", "rv", "realized_vol", "skew", "pc_ratio", "pcr",
    "liquidation", "liquidations", "liq", "volume", "gex", "max_pain",
    "long_short", "ls_ratio",
)


def _read_raw(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text())
        items = payload
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            items = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise ValueError(f"{path.name}: JSON has no list of records")
        return pd.DataFrame(items)
    return pd.read_csv(path)


def _timestamp(df: pd.DataFrame) -> pd.Series:
    col = next((c for c in df.columns if c.lower() in TIMESTAMP_COLS), None)
    if col is None:
        raise ValueError(f"no timestamp column in {list(df.columns)}")
    raw = df[col]
    if pd.api.types.is_numeric_dtype(raw):
        unit = "ms" if raw.dropna().median() > 1e11 else "s"
        return pd.to_datetime(raw, unit=unit, utc=True)
    return pd.to_datetime(raw, utc=True, format="mixed")


def _token_from_name(path: Path) -> str | None:
    stem = path.stem.lower()
    stem = re.sub(r"\d{4}[-_]?\d{2}[-_]?\d{2}", "", stem)  # strip dates
    parts = [p for p in re.split(r"[_\-\s.]+", stem) if p]
    for metric in METRIC_TOKENS:
        metric_parts = metric.split("_")
        if parts[: len(metric_parts)] == metric_parts:
            parts = parts[len(metric_parts):]
        elif parts[-len(metric_parts):] == metric_parts:
            parts = parts[: -len(metric_parts)]
    parts = [p for p in parts if p not in ("historical", "data", "export", "laevitas")]
    return parts[0].upper() if parts else None


def _token_of(df: pd.DataFrame, path: Path) -> str:
    col = next((c for c in df.columns if c.lower() in TOKEN_COLS), None)
    if col is not None:
        values = df[col].dropna().astype(str).str.upper().unique()
        # "BTC-PERPETUAL" / "BTCUSDT" -> "BTC"
        cleaned = sorted({re.split(r"[-_/]", v)[0].replace("USDT", "").replace("USD", "") or v for v in values})
        if len(cleaned) == 1:
            return cleaned[0]
    token = _token_from_name(path)
    if token is None:
        raise ValueError(f"{path.name}: cannot tell which token this is; add a currency column or put the ticker in the filename")
    return token


def _indicator_frame(df: pd.DataFrame, price_col: str | None, source: str) -> pd.DataFrame:
    drop = {c for c in df.columns if c.lower() in TIMESTAMP_COLS or c.lower() in TOKEN_COLS}
    if price_col:
        drop.add(price_col)
    numeric = df.drop(columns=list(drop), errors="ignore").apply(pd.to_numeric, errors="coerce")
    numeric = numeric.dropna(axis=1, how="all")
    # Bare tenor numbers ("7", "30") collide across files; namespace them.
    numeric.columns = [
        f"{source}_{c}" if re.fullmatch(r"\d+", str(c)) else str(c)
        for c in numeric.columns
    ]
    return numeric


def load_inbox(inbox: Path) -> dict[str, pd.DataFrame]:
    """Return {token: panel}. Panel columns: price + one per indicator."""
    files = sorted(p for p in Path(inbox).iterdir() if p.suffix.lower() in (".csv", ".json") and not p.name.startswith("."))
    if not files:
        raise FileNotFoundError(f"no CSV or JSON files in {inbox}")

    per_token: dict[str, list[pd.DataFrame]] = {}
    for path in files:
        raw = _read_raw(path)
        raw.columns = [str(c).strip() for c in raw.columns]
        ts = _timestamp(raw)
        token = _token_of(raw, path)
        price_col = next((c for c in raw.columns if c.lower() in PRICE_COLS), None)

        frame = _indicator_frame(raw, price_col, path.stem.lower())
        frame.index = ts
        if price_col:
            frame.insert(0, "price", pd.to_numeric(raw[price_col], errors="coerce").values)
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        per_token.setdefault(token, []).append(frame)

    panels = {}
    for token, frames in per_token.items():
        panel = frames[0]
        for extra in frames[1:]:
            overlap = [c for c in extra.columns if c in panel.columns and c != "price"]
            extra = extra.rename(columns={c: f"{c}_{extra.attrs.get('src', 'b')}" for c in overlap})
            panel = panel.join(extra, how="outer")
        price_cols = [c for c in panel.columns if c == "price" or c.startswith("price")]
        if not price_cols:
            raise ValueError(f"{token}: no price column in any file. Add a file with a price/close/index column.")
        panel["price"] = panel[price_cols].bfill(axis=1).iloc[:, 0]
        panel = panel.drop(columns=[c for c in price_cols if c != "price"])
        panel = panel.dropna(subset=["price"]).sort_index()
        panels[token] = panel
    return panels
