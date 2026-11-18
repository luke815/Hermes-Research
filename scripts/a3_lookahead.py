"""A3 lookahead evidence, written by this script.

The harness lives in tests/test_derivatives_lookahead.py. This script reruns
it on a temp copy of nothing: it plants a store, perturbs every raw row after
the midpoint with seeded noise, rebuilds market_measures for BTC and ETH, and
records whether any value up to that day moved. A centred window on the same
store is the negative control, and it must move. derivatives.RAW is put back
before the result is written.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from regime_tester import derivatives  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from test_derivatives_lookahead import (  # noqa: E402
    _perturb, _plant, _unchanged, market_measures,
)

import tempfile
from pathlib import Path


SCALE_FREE = (
    "rv_ratio_7_30_btc", "rv_ratio_7_30_eth",
    "atm_inversion_btc", "atm_inversion_eth",
)


def run():
    saved = derivatives.RAW
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            idx = _plant(src, n=80, seed=3)
            cutoff = idx[len(idx) // 2]
            dest = Path(tmp) / "dest"
            _perturb(src, dest, cutoff, seed=11)

            derivatives.RAW = src
            base = market_measures()
            derivatives.RAW = dest
            again = market_measures()
            held = _unchanged(base, again, cutoff)

            def centred():
                raw = derivatives.daily("dvol_btc*.json", lambda r: r.get("dvol"))
                return raw.rolling(5, center=True).mean().to_frame("leaky")

            derivatives.RAW = src
            leak_base = centred()
            derivatives.RAW = dest
            leak_again = centred()
            centred_rejected = not _unchanged(leak_base, leak_again, cutoff)

            moved_after = {}
            for name in SCALE_FREE:
                after = again[name].loc[again.index > cutoff]
                before = base[name].reindex(after.index)
                moved_after[name] = not after.fillna(0).equals(before.fillna(0))
    finally:
        derivatives.RAW = saved

    return {
        "assets": ["btc", "eth"],
        "measures": int(base.shape[1]),
        "bars": int(len(base)),
        "cutoff": str(cutoff.date()),
        "perturbation": "seeded_noise",
        "seed": 11,
        "unchanged_up_to_t": bool(held),
        "centred_window_rejected": bool(centred_rejected),
        "scale_free_moved_after_t": moved_after,
        "raw_restored": derivatives.RAW == saved,
    }


def main():
    out = run()
    if not out["unchanged_up_to_t"] or not out["centred_window_rejected"]:
        raise SystemExit("harness failed: " + json.dumps(out))
    if not all(out["scale_free_moved_after_t"].values()):
        raise SystemExit("scale-free measures did not move after t: " + json.dumps(out))
    path = write_result("a3_lookahead", out, inputs=["regime_tester/derivatives.py"])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
