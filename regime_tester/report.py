"""Render score tables to markdown. Thin cells are marked, not hidden."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _fmt(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_no result_\n"
    shown = frame.copy()
    for col in ("mean_fwd_return", "edge_vs_base", "hit_rate", "hit_edge"):
        if col in shown:
            shown[col] = shown[col].map(lambda v: f"{v:.4f}")
    if "tstat" in shown:
        shown["tstat"] = shown["tstat"].map(lambda v: f"{v:.2f}")
    shown["thin"] = shown["thin"].map(lambda v: "yes" if v else "")
    header = "| " + " | ".join(shown.columns) + " |"
    rule = "| " + " | ".join("---" for _ in shown.columns) + " |"
    body = "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in shown.itertuples(index=False))
    return "\n".join([header, rule, body]) + "\n"


def write_report(token: str, horizon: int, alone: pd.DataFrame, combos: pd.DataFrame, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {token} regime test",
        "",
        f"Forward return horizon: {horizon} bars ahead. Features are shifted by one, so a "
        "signal never sees the bar it is scored against. Regimes are walk-forward quintiles "
        "(0 = lowest trailing, 4 = highest). `thin = yes` means under 30 observations; "
        "ignore the t-stat there.",
        "",
        "## Isolation",
        "",
        _fmt(alone.sort_values("tstat", key=lambda s: s.abs(), ascending=False) if not alone.empty else alone),
        "## Combinations",
        "",
        "Agreement: every leg in an extreme quintile and all pointing the same way. "
        "Regime +1 / -1 is the agreed direction.",
        "",
        _fmt(combos.sort_values("tstat", key=lambda s: s.abs(), ascending=False) if not combos.empty else combos),
    ]
    path = out / f"{token}.md"
    path.write_text("\n".join(lines))
    if not alone.empty:
        alone.to_csv(out / f"{token}_isolation.csv", index=False)
    if not combos.empty:
        combos.to_csv(out / f"{token}_combinations.csv", index=False)
    return path
