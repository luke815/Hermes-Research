"""Add the missing Done-when clauses to R2 through R6.

The clauses are copied from research/RISK_REGIME.md sections 2 to 4 and 6,
which is where those items are specified. Each part names the file or the
number that proves it. This script only writes the clauses. Committed
before any claim of those items, because done_check reads the clause as it
stood at the claim.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")

CLAUSES = {
    "- R2. ": (
        "Done when a committed script computes the state machine in "
        "research/RISK_REGIME.md section 2 from the R1 inputs, with the "
        "hysteresis bands and the five-day minimum between changes, and the "
        "dial scaled by the ratio of target vol to 30-day realized vol, "
        "capped at 1.3 and floored at 0.5; the risk key carries state, dial, "
        "days_in_state, rules_fired, vol_scalar and emergency_cut with the "
        "panel's as_of; a scheduler slot runs it daily; "
        "results/<date>_r2_state.json is written by that script through "
        "write_result and names the state, the dial and the rules that set "
        "it."),
    "- R3. ": (
        "Done when regime_tester/strategy.py runs an exposure series times "
        "next-day returns, net of the costs table on every change in "
        "exposure and of funding carry, with the buy-and-hold benchmark and "
        "the 200-day rule on the same dates; a test shows a constant "
        "exposure of 1 matches buy and hold apart from the opening cost, and "
        "a change in exposure is charged; results/<date>_r3_harness.json is "
        "written by the script that ran it through write_result."),
    "- R4. ": (
        "Done when a committed script scores the eight variants in "
        "research/RISK_REGIME.md section 3 on BTC, ETH, the alt basket and "
        "the blend, three periods and per year, with the event view against "
        "the episode counter; results/<date>_r4_variants.json is written by "
        "that script through write_result and carries the admission verdict "
        "against beating buy and hold on maximum drawdown and Calmar in "
        "validation and in test, and beating the 200-day rule on Calmar in "
        "both."),
    "- R5. ": (
        "Done when a committed script writes the ten most recent analog "
        "dates with the blend's forward 10-day and 30-day return, the paper "
        "track from the day the risk key first existed, and the transitions; "
        "the risk key carries analogs, paper and transitions; a state change "
        "and an emergency cut are posted with the inputs that caused them; "
        "results/<date>_r5_live.json is written by that script through "
        "write_result."),
    "- R6. ": (
        "Done when the weekly note carries the week's state changes, the "
        "whipsaws, the paper track against the backtest expectation, and any "
        "input that has been unavailable, and results/<date>_r6_weekly.json "
        "is written by the script that built the note through write_result."),
}


def main():
    lines = open(BACKLOG).read().splitlines()
    changed = []
    for prefix, clause in CLAUSES.items():
        matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(matches) != 1:
            raise SystemExit(f"{prefix} matched {len(matches)} lines")
        line = lines[matches[0]]
        if "Done when" in line:
            raise SystemExit(f"{prefix} already has a Done-when clause")
        head, _, rest = line.partition(". ")
        title, _, tail = rest.partition(". ")
        if not title:
            raise SystemExit(f"{prefix} has no title sentence")
        lines[matches[0]] = f"{head}. {title}. {clause}" + (f" {tail}" if tail else "")
        changed.append(prefix.strip("-. "))
    open(BACKLOG, "w").write("\n".join(lines) + "\n")
    print("clauses added:", ", ".join(changed))


if __name__ == "__main__":
    main()
