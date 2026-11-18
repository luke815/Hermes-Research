"""Probe the v2 host once per user agent and record the status, never the key.

The earlier note said apiv2.laevitas.ch returns 403 from this machine. A full
ISO window returns 200 for both agents, and a bare date returns 400, so the
key is accepted and the 403 was a bad request. The key is read from the
environment file and sent; it is never written to the results file or the log.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "https://apiv2.laevitas.ch/api/v1/derivatives/funding-history"
AGENTS = (("default", "Python-urllib/3.14"), ("mozilla", "Mozilla/5.0"))


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LAEVITAS_API_KEY missing")


def window(today):
    """A short closed window with full ISO timestamps. A bare date returns 400."""
    end = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start = end - timedelta(days=7)
    return start.strftime("%Y-%m-%dT00:00:00Z"), end.strftime("%Y-%m-%dT00:00:00Z")


def url_for(start, end):
    return (f"{HOST}?series=futures_annualized_basis&currency=BTC&days=90"
            f"&resolution=1d&start={start}&end={end}&limit=5&page=1")


def probe(agent, url, token):
    """One GET. Returns the status and the first 200 characters of the body."""
    req = urllib.request.Request(url, headers={"X-API-Key": token, "User-Agent": agent})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    body = raw.decode("utf-8", "replace")[:200]
    return status, body


def run(today=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start, end = window(today)
    url = url_for(start, end)
    token = key()
    probes = []
    for name, agent in AGENTS:
        status, body = probe(agent, url, token)
        probes.append({"agent": name, "user_agent": agent, "status": status, "body": body})
    from regime_tester.results_io import write_result
    payload = {"item": "L12", "host": "apiv2.laevitas.ch",
               "path": "/api/v1/derivatives/funding-history", "header": "X-API-Key",
               "note": "A full ISO window. A bare date returns 400, not 403.",
               "probes": probes}
    return write_result("l12_v2", payload, inputs=["data/laevitas/INVENTORY.md"])


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    print(run())
