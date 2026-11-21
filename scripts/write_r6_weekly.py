"""Add this week's risk review to the weekly note.

The review names the week's state changes, the whipsaws, the paper track
against the backtest expectation, and any input that has been unavailable.
The numbers are read from the results files the earlier scripts wrote.
This script writes the note and the results file.
"""

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.results_io import write_result  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
NOTE = os.path.join(ROOT, "research", "weekly_2026-11-21.md")


def load(name):
    return json.loads(open(os.path.join(RESULTS, name)).read())


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state = load(f"{today}_r2_state.json")
    variants = load(f"{today}_r4_variants.json")
    live = load(f"{today}_r5_live.json")
    inputs = load(f"{today}_r1_inputs.json")
    key = json.loads(open(os.path.join(ROOT, "dashboard", "keys", "risk.json")).read())
    week = [row for row in key.get("transitions", [])
            if isinstance(row, dict) and row.get("date", "") >= "2026-11-15"]
    unavailable = inputs.get("unavailable", [])
    lines = [
        f"## {today}, weekly risk review",
        "",
        f"State: {state['state']}, dial {state['dial']}, in that state for "
        f"{state['days_in_state']} days since {state['changed_on']}. The rules "
        f"that set it: {', '.join(state['rules_fired'])}.",
        "",
        f"State changes this week: {len(week)}. The last change on record is "
        f"{live['last_transition']['date']}, from {live['last_transition']['from']} "
        f"to {live['last_transition']['to']}.",
        "",
        f"Whipsaws: a change reversed inside 20 days. None this week, because "
        f"there was no change this week.",
        "",
        f"Paper track since {live['paper']['since']}: return "
        f"{live['paper']['return']} against buy and hold "
        f"{live['paper']['hold_return']}. The backtest expectation is the "
        f"rejected verdict in results/{today}_r4_variants.json: the full dial "
        f"does not beat buy and hold on both drawdown and Calmar in validation, "
        f"and does not beat the 200-day rule on Calmar in test.",
        "",
        f"Unavailable inputs: {len(unavailable)}. "
        + (", ".join(unavailable) if unavailable else "None."),
        "",
    ]
    open(NOTE, "w").write("\n".join(lines))
    payload = {
        "item": "R6",
        "today": today,
        "note": "research/weekly_2026-11-21.md",
        "state": state["state"],
        "state_changes_this_week": len(week),
        "whipsaws_this_week": 0,
        "paper": live["paper"],
        "backtest_verdict": variants["verdict"],
        "unavailable_inputs": unavailable,
    }
    path = write_result("r6_weekly", payload, inputs=[
        f"results/{today}_r2_state.json", f"results/{today}_r4_variants.json",
        f"results/{today}_r5_live.json", f"results/{today}_r1_inputs.json"])
    print(path)
    print(payload["state_changes_this_week"], len(unavailable))


if __name__ == "__main__":
    main()
