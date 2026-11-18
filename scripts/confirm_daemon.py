"""Confirmation daemon. One eligible cell per cycle, no model involved.

Cross-sectional and event cells come first. A single-name cell is only tried
once every cross-sectional survivor on the leaderboard has been attempted.
A cell already in the confirmation record is skipped, and one whose expected
validation count is under 30 is never queued.

Usage: python3 scripts/confirm_daemon.py
"""

import json
import os
import sys

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "results", "sweeps", "leaderboard.json")
RECORD = os.path.join(ROOT, "results", "sweeps", "confirmations.json")


def attempted():
    """Cells with a live verdict. A void row is not an attempt."""
    if not os.path.exists(RECORD):
        return set()
    return {row["cell_id"] for row in json.load(open(RECORD))
            if not str(row.get("verdict", "")).startswith("void")}


def closed_cells():
    """Cells with a rejected verdict, parsed for the neighbour check.

    A void row is not closed: the current scorer has not judged it, so a
    neighbour of it is still a real test.
    """
    if not os.path.exists(RECORD):
        return []
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from pick_next_cell import parse
    return [parse(row["cell_id"]) for row in json.load(open(RECORD))
            if row.get("verdict") == "rejected"]


def is_closed_neighbour(cell_id, closed):
    """True when the cell differs from a closed one on one adjacent axis only."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from pick_next_cell import is_neighbour, parse
    cell = parse(cell_id)
    return any(is_neighbour(cell, other) for other in closed)


def eligible():
    board = json.load(open(BOARD)).get("leaderboard", [])
    done = attempted()
    closed = closed_cells()
    fresh = [row for row in board if row["cell_id"] not in done
             and row.get("status") != "insufficient"
             and not is_closed_neighbour(row["cell_id"], closed)
             and not row["cell_id"].split("|")[4].startswith(("rel_", "ratio_btc"))]
    cross = [row for row in fresh if row.get("universe") == "pit_cross_section"
             or "pit_cross_section" in row["cell_id"]]
    events = [row for row in fresh if row["cell_id"].split("|")[4].startswith(("top_", "bottom_"))]
    single = [row for row in fresh if row not in cross and row not in events]
    return cross + events + single


def _record_void(cell_id, reason):
    """Write a void row for a cell the current panel cannot score."""
    from datetime import datetime, timezone
    rows = json.load(open(RECORD)) if os.path.exists(RECORD) else []
    rows.append({
        "cell_id": cell_id,
        "verdict": "void",
        "void_reason": reason,
        "voided_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    _save(RECORD, rows)


BATCH = 40
PARTIAL = os.path.join(ROOT, "ops", "confirm_partial.json")
PANEL_DIR = os.path.join(ROOT, "ops", "confirm_panel")


def _save(path, payload):
    tmp = path + ".tmp"
    json.dump(payload, open(tmp, "w"))
    os.replace(tmp, path)


_PANEL = {}


def _panel_dir(cell_id):
    return os.path.join(PANEL_DIR, cell_id.replace("|", "_"))


def _store_batch(cell_id, panel):
    """Write one batch to disk so a restart resumes the same cell."""
    dest = _panel_dir(cell_id)
    os.makedirs(dest, exist_ok=True)
    for name, frame in panel.items():
        frame.to_csv(os.path.join(dest, f"{name}.csv"), index=False)


def _read_panel(cell_id):
    dest = _panel_dir(cell_id)
    if not os.path.isdir(dest):
        return {}
    panel = {}
    for name in sorted(os.listdir(dest)):
        if name.endswith(".csv"):
            panel[name[:-4]] = pd.read_csv(os.path.join(dest, name))
    return panel


def _listing_spans():
    """(listed_from, listed_to) per panel column, from the span files."""
    from regime_tester.pit import span_rows
    spans = {}
    for row in span_rows().itertuples(index=False):
        spans[f"{row.exchange}_{row.symbol}"] = (row.listed_from, row.listed_to)
    return spans


def cycle(ctx):
    """One batch of one cross-sectional cell. A killed run resumes the cell.

    The panel is loaded once and kept, because reading it again each cycle
    costs more than the batch itself.
    """
    queue = eligible()
    if not queue:
        return {"cell": None, "remaining": 0}
    cell = queue[0]
    if "pit_cross_section" not in cell["cell_id"]:
        from regime_tester.confirm import confirm_cell, family_attempts, family_of
        family = family_of(cell["cell_id"])
        record = confirm_cell(cell["cell_id"], family_n=family_attempts().get(family, 0),
                              train_sign=1 if cell.get("train_score", 0) > 0 else -1)
        return {"cell": cell["cell_id"], "verdict": record["verdict"],
                "family": family, "remaining": len(queue) - 1}
    from regime_tester.confirm import _load_cross_batch, confirm_cell, family_attempts, family_of
    source = "/opt/data/workspace/regime-tester/data/panel_xs_laevitas"
    if not os.path.isdir(source):
        source = os.path.join(ROOT, "data", "panel_xs")
    state = json.load(open(PARTIAL)) if os.path.exists(PARTIAL) else {}
    if state.get("cell_id") != cell["cell_id"]:
        state = {"cell_id": cell["cell_id"], "done": []}
    pending = [name[:-4] for name in sorted(os.listdir(source))
               if name[:-4] not in set(state["done"])]
    batch = pending[:BATCH]
    panel = _load_cross_batch(batch)
    _store_batch(cell["cell_id"], panel)
    state["done"] = sorted(set(state["done"]) | set(batch))
    _save(PARTIAL, {"cell_id": state["cell_id"], "done": state["done"]})
    if len(pending) > BATCH:
        return {"cell": cell["cell_id"], "batch": len(batch),
                "done": len(state["done"]), "remaining_names": len(pending) - BATCH}
    import shutil
    try:
        record = confirm_cell(cell["cell_id"],
                              family_n=family_attempts().get(family_of(cell["cell_id"]), 0),
                              train_sign=1 if cell.get("train_score", 0) > 0 else -1,
                              panel=_read_panel(cell["cell_id"]),
                              spans=_listing_spans())
        verdict = record["verdict"]
    except (ValueError, RuntimeError) as exc:
        _record_void(cell["cell_id"], f"{type(exc).__name__}: {exc}")
        verdict = "void"
    os.remove(PARTIAL)
    shutil.rmtree(_panel_dir(cell["cell_id"]), ignore_errors=True)
    return {"cell": cell["cell_id"], "verdict": verdict,
            "names": len(state["done"]), "remaining": len(queue) - 1}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("confirm", interval_sec=300, cycle=cycle, align=False)
