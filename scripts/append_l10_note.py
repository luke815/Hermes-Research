"""Append this run's reading of L10 to its backlog line.

The 05:35 slot refilled real days, and the scheduler then overwrote the
script's results file. The note names the file that records both.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = ("Rechecked 2026-11-19 02:00 UTC: the 05:35 slot has not fired today. "
          "scheduler pid 14052, alive, version c8a2e6e, next slot 2026-11-19 05:35 UTC. "
          "Unblocks when results/2026-11-19_laevitas_refresh.json shows a refilled day.")
NOTE = (" Rechecked 2026-11-19 15:00 UTC: the 05:35 slot ran. "
        "results/2026-11-19_l10_slot.json shows slot_ran true and refilled_stems "
        "rr_btc, rr_eth, atm_iv_btc, atm_iv_eth, iv_rv_btc, iv_rv_eth, with the "
        "window complete. The scheduler wrote its own record over "
        "results/2026-11-19_laevitas_refresh.json, so the script's result was gone; "
        "scripts/laevitas_refresh.py now writes l10_refresh, which that record does not cover.")


def main():
    text = open(PATH).read()
    if "results/2026-11-19_l10_slot.json shows slot_ran" in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
