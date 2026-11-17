"""Update only setups and the hourly job line in dashboard/data.json. Append ops/hourly.log.

generated_at is the data build time and belongs to build_data_json; this job
used to overwrite it every hour, so the page's "Generated" stamp showed the
health check, not the data. The hourly time now goes to meta.touched_at. The
job list is merged by name, so the daily refresh line is no longer dropped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_io import locked, read, write_atomic  # noqa: E402

ROOT = Path("/opt/data/workspace/regime-tester")


def main() -> None:
    src = ROOT / "dashboard" / "data.json"
    hourly_files = sorted((ROOT / "results").glob("*_hourly.json"))
    if not hourly_files:
        raise SystemExit("no hourly results file")
    hourly = json.loads(hourly_files[-1].read_text())
    job = {
        "name": "hourly-health",
        "written_utc": hourly["written_utc"],
        "status": "OK",
        "panel_end": hourly["panel_end"],
        "age_days": hourly["age_days"],
        "heat": hourly["heat"],
        "zone": hourly["zone"],
        "qualifying_setups": hourly["qualifying_setups"],
    }
    with locked(src):
        data = read(src)
        data["setups"] = []
        data["jobs"] = [j for j in data.get("jobs", []) if j.get("name") != job["name"]] + [job]
        meta = data.setdefault("meta", {})
        meta["touched_at"] = hourly["written_utc"]
        meta.setdefault("as_of", {}).update({"setups": hourly["written_utc"], "jobs": hourly["written_utc"]})
        write_atomic(src, data)
    line = (
        f"{hourly['written_utc']} heat={hourly['heat']:.6f} zone={hourly['zone']} "
        f"panel_end={hourly['panel_end']} age={hourly['age_days']}d "
        f"qualifying={hourly['qualifying_setups']} delta={hourly['heat_delta_vs_prior_run']}\n"
    )
    log = ROOT / "ops" / "hourly.log"
    with log.open("a") as handle:
        handle.write(line)
    print("renamed", src.stat().st_size, data.get("generated_at"), data.get("panel_end"))
    print("log_line", line.strip())


if __name__ == "__main__":
    main()
