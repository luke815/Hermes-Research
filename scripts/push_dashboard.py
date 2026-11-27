"""Commit dashboard/data.json and push to origin. Token from env, never printed.

Remote is restored to the plain URL even if the push fails.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester/dashboard")
PLAIN = "https://github.com/luke815/Hermes-Dashboard-1.git"
ENV = Path("/opt/data/.env")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("GITHUB_TOKEN="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if not value:
                raise SystemExit("GITHUB_TOKEN empty")
            return value
    raise SystemExit("GITHUB_TOKEN missing")


def main() -> None:
    message = os.environ["COMMIT_MSG"]
    secret = token()
    authed = "https://x-access-token:" + secret + "@github.com/luke815/Hermes-Dashboard-1.git"
    git("-c", "user.name=Hermes", "-c", "user.email=hermes@local", "add", "--", "data.json")
    staged = git("diff", "--cached", "--name-only").stdout.strip().splitlines()
    if staged != ["data.json"]:
        raise SystemExit(f"unexpected staged files: {staged}")
    commit = git(
        "-c", "user.name=Hermes", "-c", "user.email=hermes@local",
        "commit", "-m", message, "--", "data.json", check=False,
    )
    print("commit_exit", commit.returncode)
    if commit.returncode != 0:
        print((commit.stderr or commit.stdout)[-400:])
        raise SystemExit(commit.returncode)
    print("commit", git("rev-parse", "--short", "HEAD").stdout.strip())
    try:
        git("remote", "set-url", "origin", authed)
        push = git("push", "origin", "HEAD:main", check=False)
        print("push_exit", push.returncode)
        err = (push.stderr or "") + (push.stdout or "")
        redacted = err.replace(secret, "[redacted]")
        print(redacted[-600:])
        if push.returncode != 0:
            raise SystemExit(push.returncode)
    finally:
        git("remote", "set-url", "origin", PLAIN)
        url = git("remote", "get-url", "origin").stdout.strip()
        print("remote_plain", url == PLAIN)
        if secret in url:
            raise SystemExit("token left in remote")


if __name__ == "__main__":
    main()
