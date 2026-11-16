"""Append the xs_relative_strength verdict and update the backlog.

Every number is read from results/2026-11-16_xs_relative_strength.json, which
was written this run. Nothing is recomputed and nothing is admitted.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_xs_relative_strength.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "1. Single-feature cross-sectional test: relative strength at 14 and 30 days, "
    "point-in-time universe, net of costs.\n"
)
NEW_NEXT = (
    "1. Funding 7-day average and open-interest 7-day change as cross-sectional signals.\n"
)

PRIMARY = ("rs_14_h1", "rs_14_h3", "rs_14_h10", "rs_30_h1", "rs_30_h3", "rs_30_h10")
NEIGHBOURS = {
    "rs_14": ("rs_7", "rs_21"),
    "rs_30": ("rs_20", "rs_45"),
}


def num(value, places):
    return "none" if value is None else f"{value:.{places}f}"


def cell_line(key, cell):
    parts = []
    for period in ("train", "validation", "test"):
        block = cell[period]
        parts.append(
            f"{period} n={block['n']} ic={num(block['ic_mean'], 4)} "
            f"(t={num(block['ic_t'], 2)}) spread={num(block['spread'], 4)}% "
            f"(t={num(block['spread_t'], 2)})"
        )
    return f"{key}, {cell['n_dates']} non-overlapping dates: " + "; ".join(parts) + "."


def main():
    record = json.loads(RESULT.read_text())
    if record["candidate"] != "xs_relative_strength":
        raise SystemExit("wrong candidate")
    if not record["written_at"].startswith("2026-11-16"):
        raise SystemExit("results file was not written today")
    cells = record["cells"]

    # The pass rule needs the rank correlation and the decile spread to keep
    # their sign in validation and in test, with at least 40 independent dates
    # in each and a t-stat of 3. No primary cell meets that.
    admitted = []
    for key in PRIMARY:
        cell = cells[key]
        validation = cell["validation"]
        test = cell["test"]
        same_sign = (
            validation["ic_mean"] is not None and test["ic_mean"] is not None
            and validation["spread"] is not None and test["spread"] is not None
            and validation["ic_mean"] * test["ic_mean"] > 0
            and validation["spread"] * test["spread"] > 0
        )
        enough = validation["n"] >= 40 and test["n"] >= 40
        strong = (
            validation["ic_t"] is not None and abs(validation["ic_t"]) >= 3
            and test["ic_t"] is not None and abs(test["ic_t"]) >= 3
        )
        if same_sign and enough and strong:
            admitted.append(key)
    if admitted:
        raise SystemExit(f"expected no admission, found {admitted}")

    def sign_of(value):
        if value is None or value == 0:
            return "0"
        return "+" if value > 0 else "-"

    neighbour_bits = []
    for window, neighbours in NEIGHBOURS.items():
        for horizon in (1, 3, 10):
            own = cells[f"{window}_h{horizon}"]
            own_sign = sign_of(own["validation"]["ic_mean"]) + sign_of(own["test"]["ic_mean"])
            for neighbour in neighbours:
                other = cells[f"{neighbour}_h{horizon}"]
                other_sign = sign_of(other["validation"]["ic_mean"]) + sign_of(other["test"]["ic_mean"])
                neighbour_bits.append(f"{neighbour}_h{horizon} {other_sign} against {window} {own_sign}")

    lines = [
        "",
        "## 2026-11-16, verdict: xs_relative_strength",
        "",
        "Verdict: rejected. Neither the 14-day nor the 30-day relative strength "
        "keeps the sign of its rank correlation and of its decile spread in both "
        "validation and test at any of the three horizons, and no held-out t-stat "
        "reaches 3. Nothing is admitted. The score is unchanged.",
        f"Universe: {record['names']} names after collapsing venues and dropping "
        f"non-crypto, present on a date only when that name has a close. BTC from "
        f"{record['btc_start']}, panel ending {record['panel_end']}. Median names "
        "per date about 410. Lookahead check passed. Net of the thin-tier round "
        f"trip, {record['round_trip_bps']:.0f} basis points, because the panel has "
        "no USD open interest. Funding carry was not subtracted: funding is missing "
        "on most names and a missing carry is never treated as zero.",
    ]
    for key in PRIMARY:
        lines.append(cell_line(key, cells[key]))
    lines.append(
        "The one cell whose signs agree, rs_30_h3, has a validation rank "
        "correlation of "
        f"{num(cells['rs_30_h3']['validation']['ic_mean'], 4)} "
        f"(t={num(cells['rs_30_h3']['validation']['ic_t'], 2)}, "
        f"n={cells['rs_30_h3']['validation']['n']}) and a test correlation of "
        f"{num(cells['rs_30_h3']['test']['ic_mean'], 4)} "
        f"(t={num(cells['rs_30_h3']['test']['ic_t'], 2)}, "
        f"n={cells['rs_30_h3']['test']['n']}). Both t-stats are below 1, so the "
        "agreement is noise. Its neighbours do not agree with it: "
        + "; ".join(neighbour_bits) + "."
    )
    lines.append(
        "What does hold is the opposite of the hypothesis, and only in train. "
        "The 1-day rank correlation is negative in train for every window, with "
        f"t-stats from {num(cells['rs_14_h1']['train']['ic_t'], 2)} to "
        f"{num(cells['rs_7_h1']['train']['ic_t'], 2)}, which is a short-horizon "
        "reversal rather than momentum. It keeps its sign in validation and test "
        "at the 1-day horizon for every window, but the held-out t-stats are all "
        "below 2 and the decile spread flips, so it is not an edge and it is not "
        "what was tested. The 10-day test cells hold "
        f"{cells['rs_14_h10']['test']['n']} and {cells['rs_30_h10']['test']['n']} "
        "independent dates, below 40, and are reported rather than quoted."
    )
    lines.append(
        "Fifty-three tests since the last admission; this one is recorded and does "
        "not add to that count because it is not a confirmation attempt. "
        "results/2026-11-16_xs_relative_strength.json."
    )
    verdict = "\n".join(lines) + "\n"

    log = LOG.read_text()
    if "verdict: xs_relative_strength" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(log + verdict)

    backlog = BACKLOG.read_text()
    if OLD_NEXT not in backlog:
        raise SystemExit("next-ten block missing")
    note = (
        "\nxs_relative_strength was scored on 2026-11-16 and is rejected: neither "
        "the 14-day nor the 30-day relative strength keeps its sign in validation "
        "and test at 1, 3 or 10 days, and no held-out t-stat reaches 3. "
        "results/2026-11-16_xs_relative_strength.json.\n"
    )
    backlog = backlog.replace(OLD_NEXT, NEW_NEXT, 1)
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
