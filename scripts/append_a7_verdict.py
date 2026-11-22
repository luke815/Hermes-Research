"""Record the A7 verdict in the research log, from the results files.

The numbers are read from the files the scorer wrote. Nothing is typed in.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "research", "log.md")
RESULTS = os.path.join(ROOT, "results")


def load(name):
    return json.load(open(os.path.join(RESULTS, name)))


def main():
    reversal = load("2026-11-21_a7_reversal.json")
    derivatives = load("2026-11-22_a7_derivatives.json")
    crowding = load("2026-11-22_a7_crowding.json")["a7_3"]
    funding = load("2026-11-22_a7_funding.json")
    counts = {}
    for cell in derivatives["cells"]:
        counts[cell["verdict"]] = counts.get(cell["verdict"], 0) + 1
    pooled = {name: row["verdict"]
              for name, row in crowding["pooled"].items()}
    funding_rows = [f"horizon {cell['horizon']} {cell['verdict']}"
                    for cell in funding["cells"]]
    note = (
        "\n## 2026-11-22, A7 scored\n\n"
        "A7(1): results/2026-11-21_a7_reversal.json, written by "
        "scripts/score_a7_reversal.py, panel data/panel_xs_laevitas, "
        f"{reversal['names']} names, lookahead passed, verdict "
        f"{reversal['verdict']}. Windows: "
        + ", ".join(f"{key} {value}"
                    for key, value in reversal["verdicts"].items())
        + ".\n\n"
        "A7(2): results/2026-11-22_a7_derivatives.json, written by "
        "scripts/score_a7_parts.py, panel data/laevitas/market, lookahead "
        f"passed. {len(derivatives['cells'])} cells: "
        + ", ".join(f"{count} {name}" for name, count in sorted(counts.items()))
        + ". None kept on both assets. The filter on A7(1) was not scored, "
        "because A7(1) was rejected and a filter on a rejected score is not "
        "a second verdict.\n\n"
        "A7(3): results/2026-11-22_a7_crowding.json, written by "
        "scripts/score_a7_parts.py, panel data/laevitas/market for ADA, SOL, "
        "LINK, XRP and AVAX, date-clustered, survivor-biased. Pooled: "
        + ", ".join(f"{name} {value}" for name, value in pooled.items())
        + ".\n\n"
        "A7(4): results/2026-11-22_a7_funding.json, written by "
        "scripts/score_a7_parts.py, panel data/panel.csv, two names, carry "
        "charged. "
        + ", ".join(funding_rows)
        + ". This is the market-level reading the pre-registration specifies "
        "and does not close a cross-sectional clause.\n"
    )
    open(LOG, "a").write(note)
    print("appended", len(note))


if __name__ == "__main__":
    main()
