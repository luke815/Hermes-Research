"""Print remote dashboard fields and the last hourly log lines. Dedup last log line if identical."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")


def main() -> None:
    remote = json.loads(Path("/tmp/dash_after.json").read_text())
    print("remote_panel_end", remote.get("panel_end"))
    print("remote_generated_at", remote.get("generated_at"))
    job = (remote.get("jobs") or [{}])[0]
    print("remote_job", job.get("written_utc"), job.get("zone"), job.get("qualifying_setups"), job.get("heat"))
    print("remote_setups", remote.get("setups"))
    log = ROOT / "ops" / "hourly.log"
    lines = log.read_text().splitlines(keepends=True)
    if len(lines) >= 2 and lines[-1] == lines[-2]:
        log.write_text("".join(lines[:-1]))
        print("deduped_log")
    tail = log.read_text().splitlines()[-3:]
    for line in tail:
        print("log", line)
    local = json.loads((ROOT / "dashboard" / "data.json").read_text())
    print("local_generated_at", local["generated_at"])
    print("local_panel_end", local["panel_end"])
    print("local_keys", ",".join(sorted(local.keys())))


if __name__ == "__main__":
    main()
