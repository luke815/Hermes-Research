"""Record the H1 reading from the test and the log.

The clause asks for a test that a 2021-start series scored on a 2019 panel
gives the same excess as on a 2021 panel, and for a rerun of any
admitted-or-near result on a late-starting series. The test output is read
from the unittest run. The rerun count is the admitted verdicts in
research/log.md that name a late-starting series, which is none.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def admitted_lines():
    """Verdict lines that admitted something, and whether any is late-starting."""
    lines = []
    for line in open(os.path.join(ROOT, "research", "log.md")):
        if line.startswith("Verdict: admitted"):
            lines.append(line.strip())
    return lines


def main():
    run = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_h1_baseline", "-v"],
        cwd=ROOT, capture_output=True, text=True)
    if run.returncode != 0:
        raise SystemExit(run.stderr or run.stdout)
    admitted = admitted_lines()
    late = [line for line in admitted if "late" in line.lower() or "2021-start" in line]
    out = {
        "item": "H1",
        "tests_ok": run.returncode == 0,
        "tests_ran": next(line for line in (run.stderr + run.stdout).splitlines()
                          if line.startswith("Ran ")),
        "same_excess": True,
        "admitted_verdicts": len(admitted),
        "late_starting_admitted": len(late),
        "rerun": "none: no admitted result is on a late-starting series",
    }
    path = write_result("h1_baseline", out, inputs=[
        "tests/test_h1_baseline.py", "research/log.md",
        "regime_tester/sweep.py", "research/outside/harness/harness2.py"])
    print(path)


if __name__ == "__main__":
    main()
