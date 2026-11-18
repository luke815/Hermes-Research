"""Load a named value from /opt/data/.env.

Every script that pushes or posts reads its token here, so a run that forgot to
source the file still has it. The value is never printed.
"""

import os

ENV = "/opt/data/.env"


def token(name):
    if os.environ.get(name):
        return os.environ[name]
    for line in open(ENV):
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{name} is not in the environment or {ENV}")
