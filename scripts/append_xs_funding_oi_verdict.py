"""Append the xs_funding_oi verdict and update the backlog.

Every number is read from results/2026-11-16_xs_funding_oi.json, which was
written this run. Nothing is recomputed and nothing is admitted.
"""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
RESULT = ROOT / "results" / "2026-11-16_xs_funding_oi.json"
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"

OLD_NEXT = (
    "1. Funding 7-day average and open-interest 7-day change as cross-sectional signals.\n"
)
NEW_NEXT = (
    "1. One-day reversal in the bottom half of the universe by open interest.\n"
)

FUNDING = ("funding_7_h1", "funding_7_h3", "funding_7_h10")
NEIGHBOURS = ("funding_3", "funding_14")


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


def sign_of(value):
    if value is None or value == 0:
        return "0"
    return "+" if value > 0 else "-"


def main():
    record = json.loads(RESULT.read_text())
    if record["candidate"] != "xs_funding_oi":
        raise SystemExit("wrong candidate")
    if not record["written_at"].startswith("2026-11-16"):
        raise SystemExit("results file was not written today")
    cells = record["cells"]
    funding = record["funding_coverage"]
    oi = record["oi_coverage"]

    # A pass needs the rank correlation and the decile spread to keep their
    # sign in validation and test, with 40 independent dates and a t-stat of 3.
    # Funding flips its sign. Open interest has no dates at all.
    for key in FUNDING:
        validation = cells[key]["validation"]
        test = cells[key]["test"]
        if validation["ic_mean"] is None or test["ic_mean"] is None:
            continue
        same_sign = validation["ic_mean"] * test["ic_mean"] > 0
        strong = (
            validation["ic_t"] is not None and abs(validation["ic_t"]) >= 3
            and test["ic_t"] is not None and abs(test["ic_t"]) >= 3
        )
        if same_sign and strong and validation["n"] >= 40 and test["n"] >= 40:
            raise SystemExit(f"expected no admission, {key} passes")
    for key in ("oi_7_h1", "oi_7_h3", "oi_7_h10"):
        if cells[key]["n_dates"] != 0:
            raise SystemExit(f"expected no oi dates, {key} has {cells[key]['n_dates']}")

    neighbour_bits = []
    for horizon in (1, 3, 10):
        own = cells[f"funding_7_h{horizon}"]
        own_sign = sign_of(own["validation"]["ic_mean"]) + sign_of(own["test"]["ic_mean"])
        for neighbour in NEIGHBOURS:
            other = cells[f"{neighbour}_h{horizon}"]
            other_sign = sign_of(other["validation"]["ic_mean"]) + sign_of(other["test"]["ic_mean"])
            neighbour_bits.append(f"{neighbour}_h{horizon} {other_sign} against funding_7 {own_sign}")

    lines = [
        "",
        "## 2026-11-16, verdict: xs_funding_oi",
        "",
        "Verdict: rejected for funding, insufficient for open interest. The "
        "7-day funding average flips the sign of its rank correlation between "
        "validation and test at all three horizons, and no held-out t-stat "
        "reaches 2, let alone 3. The 7-day open-interest change has no date "
        "with 20 names, so it has no spread to score. Nothing is admitted. "
        "The score is unchanged.",
        f"Universe: {record['names']} names after collapsing venues and dropping "
        f"non-crypto. Funding covers {funding['names']} names, earliest "
        f"{funding['earliest']}, latest end {funding['latest_end']}, "
        f"{funding['ending_in_test']} of them still printing in the test period, "
        f"median {funding['median_rows']} rows. Open interest covers {oi['names']} "
        f"names, all stopped, latest end {oi['latest_end']}, and only "
        f"{oi['ending_in_test']} reach the test period. Median names per date "
        f"on the funding cells is {cells['funding_7_h1']['names_median']:.0f}. "
        "Lookahead check passed. Net of the thin-tier round trip, "
        f"{record['round_trip_bps']:.0f} basis points, because the live names "
        "have no USD open interest. Funding carry was not subtracted: a missing "
        "carry is never treated as zero.",
    ]
    for key in FUNDING:
        lines.append(cell_line(key, cells[key]))
    lines.append(
        "The sign the hypothesis wanted, a negative rank correlation, is the "
        "train and validation sign at every primary horizon, and it is the "
        "wrong sign in test at every one of them. The largest held-out t-stat "
        f"is {num(cells['funding_7_h1']['test']['ic_t'], 2)} on "
        f"{cells['funding_7_h1']['test']['n']} independent dates, and it points "
        "the wrong way. The decile spread agrees with the correlation in "
        "validation at 3 and 10 days and disagrees at 1 day, and it is positive "
        "in test at all three, so the two statistics do not rescue each other. "
        "The 10-day test cell holds "
        f"{cells['funding_7_h10']['test']['n']} independent dates, below 40, "
        "and is reported rather than quoted. Neighbours: "
        + "; ".join(neighbour_bits) + ". The 3-day mean flips its validation "
        "sign at the 1-day horizon, so the neighbour check fails there too."
    )
    lines.append(
        f"Open interest is saved for {oi['names']} stopped names and never "
        "reaches 20 names on one date, which is the minimum the scorer requires "
        "before it writes a row. All three horizons and both neighbours have "
        "zero dates. The cell is insufficient, not a rejection, and it stays "
        "blocked until the live-name open-interest pull lands."
    )
    lines.append(
        "Fifty-three tests since the last admission; this one is recorded and "
        "does not add to that count because it is not a confirmation attempt. "
        "results/2026-11-16_xs_funding_oi.json."
    )
    verdict = "\n".join(lines) + "\n"

    log = LOG.read_text()
    if "verdict: xs_funding_oi" in log:
        raise SystemExit("verdict already written")
    LOG.write_text(verdict + log)

    backlog = BACKLOG.read_text()
    if OLD_NEXT not in backlog:
        raise SystemExit("next-ten block missing")
    note = (
        "\nxs_funding_oi was scored on 2026-11-16 and is rejected for funding "
        "and insufficient for open interest: the 7-day funding average flips "
        "sign between validation and test at 1, 3 and 10 days, and the 7-day "
        "open-interest change has no date with 20 names. "
        "results/2026-11-16_xs_funding_oi.json.\n"
    )
    backlog = backlog.replace(OLD_NEXT, NEW_NEXT, 1)
    backlog = backlog.replace("## Queue\n", "## Queue\n" + note, 1)
    BACKLOG.write_text(backlog)
    print("log", LOG.stat().st_size, "backlog", BACKLOG.stat().st_size)


if __name__ == "__main__":
    main()
