"""Push both repositories, loading the token from /opt/data/.env itself.

Every run and daemon calls this instead of pushing by hand, so a run that
forgot to source the file still pushes, and a failed push is visible as a
non-zero exit the next run retries.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_token import token

REPOS = {
    "research": "/opt/data/workspace/regime-tester",
    "dashboard": "/opt/data/workspace/regime-tester/dashboard",
}
REMOTES = {
    "research": "https://github.com/luke815/Hermes-Research.git",
    "dashboard": "https://github.com/luke815/Hermes-Dashboard-1.git",
}


def push(name):
    repo = REPOS[name]
    url = REMOTES[name].replace("https://", "https://x-access-token:" + token("GITHUB_TOKEN") + "@")
    result = subprocess.run(["git", "push", url, "HEAD:main"], cwd=repo, capture_output=True, text=True)
    subprocess.run(["git", "remote", "set-url", "origin", REMOTES[name]], cwd=repo)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"{name} push failed")
    return result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "up to date"


if __name__ == "__main__":
    for repo in REPOS:
        print(repo, push(repo))
