"""Shared call budget for every market-data pull.

One token bucket at 30 calls per minute, held in a file lock so every script
on this machine draws from the same budget. A 429 is pacing, not failure:
honour Retry-After exactly once, then stop. The caller keeps what it has
already written and resumes on the next run. No call is ever retried twice
inside one run.
"""

import fcntl
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BUDGET_PER_MINUTE = 22
RESERVED_PER_MINUTE = 8
STATE = "/opt/data/workspace/regime-tester/data/rate_bucket.json"
LOCK = STATE + ".lock"


def _take(now, allowance):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(LOCK, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        except json.JSONDecodeError:
            state = {}
        stamps = state.setdefault(allowance, [])
        cap = RESERVED_PER_MINUTE if allowance == "live" else BUDGET_PER_MINUTE
        window = [t for t in stamps if now - t < 60]
        wait = 0.0
        if len(window) >= cap:
            wait = 60 - (now - window[0]) + 0.1
        else:
            window.append(now)
            state[allowance] = window
            json.dump(state, open(STATE + ".tmp", "w"))
            os.replace(STATE + ".tmp", STATE)
        fcntl.flock(lock, fcntl.LOCK_UN)
    return wait


def acquire(allowance="shared"):
    """Block until the named allowance has a token.

    The live daemon draws from its own reserved allowance. Every other pull
    draws from the shared one. The two never compete, so a busy research pull
    cannot starve the live board and the board cannot trip a research pull.
    """
    while True:
        wait = _take(time.time(), allowance)
        if wait <= 0:
            return
        time.sleep(wait)


def get(url, headers=None, timeout=90, allowance="shared"):
    """One GET. Returns the response body, or raises BudgetStop on a second 429.

    allowance names the bucket: "shared" for every pull but the live daemon,
    "live" for the daemon's reserved allowance.
    """
    acquire(allowance)
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "hermes"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 429:
            raise
        wait = float(exc.headers.get("Retry-After", "30")) + 1
        print(f"429, honoured Retry-After once ({wait:.0f}s), then stopping", flush=True)
        time.sleep(wait)
        acquire(allowance)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as again:
            if again.code == 429:
                raise BudgetStop(f"429 twice on {url.split('?')[0]}")
            raise


def get_json(url, headers=None, timeout=90, allowance="shared"):
    return json.loads(get(url, headers, timeout, allowance))


class BudgetStop(RuntimeError):
    """The budget or the vendor said stop. What is on disk stands."""


def coinalyze(path, params, key, allowance="shared"):
    params = dict(params, api_key=key)
    url = "https://api.coinalyze.net/v1/" + path + "?" + urllib.parse.urlencode(params)
    return get_json(url, timeout=90, allowance=allowance)
