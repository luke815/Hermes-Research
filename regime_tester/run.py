"""Entry point. Reads data/inbox, writes reports/."""

from __future__ import annotations

import argparse
from pathlib import Path

from .load import load_inbox
from .report import write_report
from .score import combinations, isolation

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward regime tester for Laevitas indicators")
    parser.add_argument("--inbox", default=str(ROOT / "data" / "inbox"))
    parser.add_argument("--out", default=str(ROOT / "reports"))
    parser.add_argument("--horizon", type=int, default=24, help="forward return in bars")
    parser.add_argument("--max-legs", type=int, default=3)
    args = parser.parse_args()

    panels = load_inbox(Path(args.inbox))
    out = Path(args.out)
    for token, panel in sorted(panels.items()):
        indicators = [c for c in panel.columns if c != "price"]
        print(f"{token}: {len(panel)} bars, {len(indicators)} indicators ({', '.join(indicators)})")
        alone = isolation(panel, args.horizon)
        kept = panel[["price", *alone["indicator"].unique()]]
        combos = combinations(kept, args.horizon, max_legs=args.max_legs)
        path = write_report(token, args.horizon, alone, combos, out)
        print(f"  -> {path}")


if __name__ == "__main__":
    main()
