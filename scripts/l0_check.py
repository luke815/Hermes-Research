"""Record whether the stall check runs and whether the digest carries its line.

Reads the health log and the digest job's output. Writes nothing it did not
read from those two files.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEALTH = os.path.join(ROOT, "ops", "health.log")
DIGEST = os.path.join(ROOT, "cron_output_digest.md")


def digest_carries_line(text, line):
    """True when the digest's response quotes the health check's line."""
    marker = "## Response"
    response = text.split(marker, 1)[1] if marker in text else ""
    return line in response


def main():
    rows = [row.strip() for row in open(HEALTH) if "stall_check item=" in row]
    last = rows[-1] if rows else ""
    item = last.split("item=", 1)[1].split(" ", 1)[0] if last else ""
    runs = last.split("runs=", 1)[1].split(" ", 1)[0] if last else ""
    line = f"top backlog item {item}, {runs} runs" if item else ""
    digest_path = sys.argv[1] if len(sys.argv) > 1 else DIGEST
    digest = open(digest_path).read() if os.path.exists(digest_path) else ""
    out = {
        "item": "L0",
        "health_log_rows": len(rows),
        "last_stall_check": last,
        "top_item": item,
        "runs": int(runs) if runs.isdigit() else None,
        "line": line,
        "digest_file": os.path.basename(digest_path),
        "digest_carries_line": digest_carries_line(digest, line) if line else False,
    }
    path = write_result("l0_check", out, inputs=["ops/health.log"])
    print(json.dumps({k: out[k] for k in ("top_item", "runs", "digest_carries_line")}))
    print(path)


if __name__ == "__main__":
    main()
