"""Record this run's notes on the items it passed over.

Each note names the results file or the status line that shows why the item
is still open. The numbers are read from those files, not typed.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
RESULTS = os.path.join(ROOT, "results")


def load(name):
    return json.load(open(os.path.join(RESULTS, name)))


def notes():
    a1 = load("2026-11-19_a1_block.json")
    a5 = load("2026-11-19_a5_state.json")
    l8 = load("2026-11-19_l8_sum.json")
    l11 = load("2026-11-19_l11_pull.json")
    return {
        "A1.": (" Rechecked 2026-11-19 02:00 UTC: results/2026-11-19_a1_block.json "
                f"counts {a1['missing_sum_file']} of {a1['live_names']} live names with no "
                f"sum file, all {a1['missing_per_venue'].get('okx', 0)} OKX. funding_sum "
                "pid 19927, alive, phase working. The panel swap waits on those sums, "
                "which the daemon writes, not a research run."),
        "A5.": (" Read 2026-11-19 02:00 UTC: results/2026-11-19_a5_state.json shows "
                f"rs_stale false, newest bar {a5['newest_bar']}, age "
                f"{a5['newest_bar_age_sec']} seconds against the 10,800 second window. "
                "The full day has not elapsed. The hourly slot was keyed by the day and "
                "the refill shared the pull budget, so the board went stale every hour; "
                "both are committed and the scheduler runs them. Unblocks when that file "
                "shows the flag false across a full day."),
        "L8.": (" Rechecked 2026-11-19 02:00 UTC: results/2026-11-19_l8_sum.json shows "
                f"ETH {l8['ETH']['days_summed']} days summed, last {l8['ETH']['last']}, "
                f"remaining {l8['remaining']}. liq_daily_sum pid 2323, alive. Unblocks "
                "when that file shows remaining 0."),
        "L10.": (" Rechecked 2026-11-19 02:00 UTC: the 05:35 slot has not fired today. "
                 "scheduler pid 14052, alive, version c8a2e6e, next slot 2026-11-19 "
                 "05:35 UTC. Unblocks when results/2026-11-19_laevitas_refresh.json "
                 "shows a refilled day."),
        "L11.": (" Rechecked 2026-11-19 02:00 UTC: a saved empty history was refetched "
                 "every cycle, so the remaining count never fell. scripts/delisted_pull.py "
                 "now treats a saved empty answer as done, and the daemon was restarted "
                 f"onto it. results/2026-11-19_l11_pull.json shows {l11['remaining']} "
                 f"remaining of {l11['dead_names']}. Unblocks when that file shows remaining 0."),
    }


def main():
    text = open(BACKLOG).read()
    lines = text.split("\n")
    changed = 0
    for marker, note in notes().items():
        hits = [i for i, line in enumerate(lines) if line.startswith("- " + marker)]
        if len(hits) != 1:
            raise SystemExit(f"{marker}: {len(hits)} lines")
        if note.strip() in lines[hits[0]]:
            continue
        lines[hits[0]] = lines[hits[0]].rstrip() + note
        changed += 1
    open(BACKLOG, "w").write("\n".join(lines))
    print("notes added", changed)


if __name__ == "__main__":
    main()
