"""Append the A7(2) and A7(4) verdict to the research log.

The numbers come from results/2026-11-20_a7_rest.json. This script only
writes them down.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "research", "log.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_a7_rest.json")


def line(cell):
    held = []
    for name in ("validation", "test"):
        row = cell["periods"][name]
        held.append(
            f"{name} {row.get('spread_independent')} "
            f"(t={row.get('t_independent')}, n={row.get('flagged_independent')})")
    return (f"{cell['feature']} {cell['transform']} {cell['side']} "
            f"{cell['asset']} {cell['horizon']}d {cell['verdict']}: "
            + "; ".join(held))


def main():
    reading = json.load(open(RESULT))
    cells = [c for c in reading["a7_2"] if not c.get("neighbour")]
    rejected = sum(1 for c in cells if c["verdict"] == "rejected")
    insufficient = sum(1 for c in cells if c["verdict"] == "insufficient")
    closest = max(
        (c for c in cells if c.get("reason")),
        key=lambda c: min(abs(c["periods"][p].get("t_independent") or 0)
                          for p in ("validation", "test")))
    entry = (
        "\n\n## 2026-11-20, pre-registered before any computation: A7(2) and A7(4)\n\n"
        "Candidate: a7_rest. Hypothesis and rule: research/outside/PREREG_A7.md, "
        f"committed as {reading['prereg_commit']} before this scoring. "
        "A7(1) was not scored: its panel has a bad close and a research run does "
        "not rewrite it. A7(3) was not scored: data/laevitas/market has no "
        "derivs_summary for ADA, SOL, LINK, XRP or AVAX.\n\n"
        f"Verdict: insufficient for A7(2), {rejected} cells rejected and "
        f"{insufficient} insufficient of {len(cells)}, none kept on both assets. "
        "The closest was the ETH basis 30-day tenor at its trailing 365-day "
        "bottom quintile, 1-day horizon, which cleared the bar on ETH and not on "
        f"BTC: {line(closest)}. "
        "A7(4) is insufficient at 1 day, t-stat 1.354197 in validation and "
        "2.39817 in test on 2 names, and rejected at 3 days, where the sign "
        "flips in validation. Lookahead passed. results/2026-11-20_a7_rest.json.\n"
    )
    current = open(LOG).read()
    if "results/2026-11-20_a7_rest.json" in current:
        raise SystemExit("entry already present")
    open(LOG, "w").write(current.rstrip() + entry)
    print("appended")


if __name__ == "__main__":
    main()
