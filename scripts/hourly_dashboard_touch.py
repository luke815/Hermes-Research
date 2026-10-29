"""Update only setups, jobs, generated_at in dashboard/data.json. Append ops/hourly.log."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")


def main() -> None:
    src = ROOT / "dashboard" / "data.json"
    data = json.loads(src.read_text())
    hourly_files = sorted((ROOT / "results").glob("*_hourly.json"))
    if not hourly_files:
        raise SystemExit("no hourly results file")
    hourly = json.loads(hourly_files[-1].read_text())
    before = set(data.keys())
    data["setups"] = []
    data["generated_at"] = hourly["written_utc"]
    data["jobs"] = [
        {
            "name": "hourly-health",
            "written_utc": hourly["written_utc"],
            "status": "OK",
            "panel_end": hourly["panel_end"],
            "age_days": hourly["age_days"],
            "heat": hourly["heat"],
            "zone": hourly["zone"],
            "qualifying_setups": hourly["qualifying_setups"],
        }
    ]
    if set(data.keys()) != before:
        raise SystemExit("key set changed")
    tmp = ROOT / "dashboard" / "data.json.tmp"
    tmp.write_text(json.dumps(data))
    tmp.replace(src)
    line = (
        f"{hourly['written_utc']} heat={hourly['heat']:.6f} zone={hourly['zone']} "
        f"panel_end={hourly['panel_end']} age={hourly['age_days']}d "
        f"qualifying={hourly['qualifying_setups']} delta={hourly['heat_delta_vs_prior_run']}\n"
    )
    log = ROOT / "ops" / "hourly.log"
    with log.open("a") as handle:
        handle.write(line)
    print("renamed", src.stat().st_size, data["generated_at"], data["panel_end"])
    print("log_line", line.strip())


if __name__ == "__main__":
    main()
