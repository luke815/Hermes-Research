"""Record this run's notes on the items it passed over.

A1, A5, L8, L10 and L11 are blocked on a daemon or on a clock, and each note
names the file or status line that shows it. E3 closed this run, so the note
that said it was not done is removed rather than left standing.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")

NOTES = {
    "A1.": (" Blocked 2026-11-19 01:00 UTC, rechecked: funding_sum pid 19927, alive, "
            "phase working, cycle 1748, walking OKX, remaining 486 in "
            "ops/logs/funding_sum.log. The panel swap waits on those sums, which the "
            "daemon writes, not a research run."),
    "A5.": (" Read 2026-11-19 01:00 UTC: results/2026-11-19_a5_state.json still shows "
            "rs_stale false with the newest bar at 2026-11-18T22:00:00Z, and the full "
            "day has not elapsed. Unblocks when that file shows the flag false across "
            "a full day."),
    "L8.": (" Rechecked 2026-11-19 01:00 UTC: liq_daily_sum pid 2323, alive, phase idle, "
            "cycle 327. results/2026-11-19_l8_sum.json still has ETH at 0 days and "
            "remaining 1. Unblocks when that file shows ETH days summed and remaining 0."),
    "L10.": (" Rechecked 2026-11-19 01:00 UTC: the 05:35 slot has not fired today. "
             "scheduler pid 4622, alive, next slot 2026-11-19 05:35 UTC. Unblocks when "
             "results/2026-11-19_laevitas_refresh.json shows a refilled day."),
    "L11.": (" Rechecked 2026-11-19 01:00 UTC: delisted_pull pid 5254, alive, phase idle, "
             "cycle 127. results/2026-11-19_l11_pull.json still shows 491 remaining. "
             "Unblocks when that file shows remaining 0."),
}


def main():
    text = open(BACKLOG).read()
    lines = text.split("\n")
    changed = 0
    for marker, note in NOTES.items():
        hits = [i for i, line in enumerate(lines) if line.startswith("- " + marker)]
        if len(hits) != 1:
            raise SystemExit(f"{marker}: {len(hits)} lines")
        if note.strip() in lines[hits[0]]:
            continue
        lines[hits[0]] = lines[hits[0]].rstrip() + note
        changed += 1
    stale = "Not done: results/2026-11-19_e3_extremes.json shows the raw file on main matches the local key and the hosted page returns 404, so the hosted key cannot be confirmed."
    if stale not in "\n".join(lines):
        raise SystemExit("stale E3 note missing")
    lines = [line.replace(stale, "") for line in lines]
    open(BACKLOG, "w").write("\n".join(lines))
    print("notes added", changed)


if __name__ == "__main__":
    main()
