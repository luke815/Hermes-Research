"""Commit this run's files and push both repositories. Token never printed."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/opt/data/workspace/regime-tester/scripts")
from env_token import token  # noqa: E402

ROOT = Path("/opt/data/workspace/regime-tester")
PATHS = [
    "research/log.md",
    "research/backlog.md",
    "results/2026-11-16_eth_drawdown_90_bottom.json",
    "scripts/eth_drawdown_90_bottom.py",
    "scripts/append_eth_drawdown_prereg.py",
    "scripts/append_eth_drawdown_verdict.py",
    "scripts/push_eth_drawdown.py",
]
MESSAGE = "eth_drawdown_90_bottom: insufficient, 14 fires across train and validation"
REPOS = {
    "research": (ROOT, "https://github.com/luke815/Hermes-Research.git"),
    "dashboard": (ROOT / "dashboard", "https://github.com/luke815/Hermes-Dashboard-1.git"),
}


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True)


def main() -> None:
    secret = token("GITHUB_TOKEN")
    git(ROOT, "-c", "user.name=Hermes", "-c", "user.email=hermes@local", "add", "--", *PATHS)
    staged = git(ROOT, "diff", "--cached", "--name-only").stdout.strip().splitlines()
    unexpected = [path for path in staged if path not in PATHS]
    if unexpected:
        git(ROOT, "reset", "-q", "HEAD", "--", *unexpected, check=False)
        raise SystemExit(f"unexpected staged files: {unexpected}")
    if sorted(staged) != sorted(PATHS):
        raise SystemExit(f"staged set mismatch: {staged}")
    commit = git(ROOT, "-c", "user.name=Hermes", "-c", "user.email=hermes@local",
                 "commit", "-m", MESSAGE, check=False)
    print("commit_exit", commit.returncode)
    if commit.returncode != 0:
        print((commit.stderr or commit.stdout)[-400:])
        raise SystemExit(commit.returncode)
    head = git(ROOT, "rev-parse", "--short", "HEAD").stdout.strip()
    print("commit", head)

    for name, (repo, plain) in REPOS.items():
        authed = plain.replace("https://", f"https://x-access-token:{secret}@")
        try:
            git(repo, "remote", "set-url", "origin", authed)
            push = git(repo, "push", "origin", "HEAD:main", check=False)
            text = ((push.stderr or "") + (push.stdout or "")).replace(secret, "[redacted]")
            print(name, "push_exit", push.returncode, text.strip().splitlines()[-1:])
            if push.returncode != 0:
                raise SystemExit(f"{name} push failed")
        finally:
            git(repo, "remote", "set-url", "origin", plain)
            url = git(repo, "remote", "get-url", "origin").stdout.strip()
            if secret in url or url != plain:
                raise SystemExit(f"{name} remote not restored")
        print(name, "remote_plain", True)
    print("HEAD", head)


if __name__ == "__main__":
    main()
