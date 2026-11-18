"""One HTTP GET for every pull, with the shared budget in front of it.

A 429 is honoured once through the budget and then stops the run. Any other
failure is retried once. A second failure raises, and the caller keeps the
parts it has already written and resumes on the next run. Nothing here retries
a third time.
"""

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rate_budget  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402


def fetch(url: str, timeout: int = 120, headers: dict | None = None) -> bytes:
    hdrs = headers or {"User-Agent": "regime-tester"}
    try:
        return rate_budget.get(url, headers=hdrs, timeout=timeout)
    except BudgetStop:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"  retry once {url.rsplit('/', 1)[-1]}: {exc}", flush=True)
        time.sleep(2)
        return rate_budget.get(url, headers=hdrs, timeout=timeout)


def atomic_text(path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(target)


def atomic_bytes(path, blob: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(blob)
    tmp.replace(target)
