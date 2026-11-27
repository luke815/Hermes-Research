"""Move the trailing run-count sentence back ahead of the new clause.

scripts/add_b3_b5_clauses.py inserted the clause before the first period,
so "One run." and "Two runs." ended up after the clause. This puts them
back between the title and the clause. It changes no part of the clause.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
TAILS = {"- B3. ": "One run. ", "- B4. ": "Two runs. ", "- B5. ": "One run. "}


def main():
    text = open(BACKLOG).read()
    lines = text.splitlines()
    for prefix, tail in TAILS.items():
        matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(matches) != 1:
            raise SystemExit(f"{prefix} matched {len(matches)} lines")
        line = lines[matches[0]]
        marker = "Done when "
        at = line.find(marker)
        if at < 0 or tail not in line[at:]:
            raise SystemExit(f"{prefix} is not in the shape this script fixes")
        if line[at - len(tail):at] == tail:
            raise SystemExit(f"{prefix} already has the sentence in place")
        fixed = line[:at] + tail + line[at:].replace(tail, "", 1)
        lines[matches[0]] = fixed
    open(BACKLOG, "w").write("\n".join(lines) + "\n")
    print("sentences restored")


if __name__ == "__main__":
    main()
