"""An item is done when done_check says so, not when a run says so.

On 2026-11-17 four items were marked done with hand-written results, tests
that could not fail, and no code. This tool runs the checks a done claim must
pass and records the outcome. A "Done" in research/backlog.md without a
matching passing record is a violation the health check reports.

    python3 scripts/done_check.py check A2 \\
        --results results/2026-11-18_a2_statistics.json \\
        --tests tests.test_confirm_cross_section \\
        --evidence "two cells differ: tests.test_confirm_cross_section.TwoCells.test_cells_differ" \\
        --evidence "void rows rescorable: results/2026-11-18_a2_statistics.json:voided" \\
        [--since <commit>] [--no-code "<one sentence>"]

    Checks, all of which must pass:
      1. every --results file exists, is named for the item, and carries a
         valid provenance stamp (written through regime_tester.results_io by
         a committed, unmodified script);
      2. every --tests module is under tests/, runs under python3 -m unittest,
         ran at least one test, and passed;
      3. commits since the claim head (or --since, which may not be newer than
         the claim head) changed a .py or .sh file under scripts/ or
         regime_tester/, unless --no-code gives a sentence;
      4. the item has exactly one "- <ITEM>." line in research/backlog.md,
         with a Done-when clause that was already there at the claim head;
         the clause's parts are separated by ";" and each part has one
         --evidence "<part>: <proof>" whose proof is a test id that ran or a
         key in a cited results file.
    On success it prints DONE-CHECK OK <item> <token> and the exact backlog
    text to paste. It writes ops/done_checks/<item>.json (a failure goes to
    <item>.fail.json and leaves a passing record alone) and appends to
    ops/done_checks.log.

    python3 scripts/done_check.py audit
        every "Done" item in the backlog must have a passing, unedited record
        whose token is in the line, and every results file an item cites must
        verify. Exit 1 and list violations.

    python3 scripts/done_check.py report <ITEM>
        the report block for the run summary, built from the record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from regime_tester.results_io import verify_result  # noqa: E402

BACKLOG = os.path.join(ROOT, "research", "backlog.md")
RECORDS = os.path.join(ROOT, "ops", "done_checks")
CLAIMS = os.path.join(ROOT, "ops", "claims")
LOG = os.path.join(ROOT, "ops", "done_checks.log")
ITEM_LINE = re.compile(r"^\s*-\s+([A-Z]{1,3}\d{1,3}[a-z]?)\.\s+(.*)$")
# "Done 2026-11-18." marks an item done. "Done when", "not done" and "Not done" do not.
DONE_MARK = re.compile(r"(?<![Nn]ot )\bDone\b(?: (\d{4}-\d{2}-\d{2}))?(?=[.,;:)]|$)")
ANY_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
# A research verdict with a date must cite results files that verify.
VERDICT_MARK = re.compile(r"\b(Admitted|Rejected|Insufficient|Void) (\d{4}-\d{2}-\d{2})")
CITATION = re.compile(r"results/[\w./-]+\.json")
# Items marked done before the guards existed are reported as one count, not one violation each.
GUARD_START = "2026-11-18"
CODE_DIRS = ("scripts/", "regime_tester/")
CODE_EXT = (".py", ".sh")


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(root, *args):
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def _ancestor(root, older, newer):
    return _git(root, "merge-base", "--is-ancestor", older, newer) is not None


def backlog_items(text):
    """{item_id: [(line_number, text), ...]} for every "- X1. ..." line, indented or not."""
    items = {}
    for number, line in enumerate(text.splitlines(), 1):
        match = ITEM_LINE.match(line)
        if match:
            items.setdefault(match.group(1), []).append((number, match.group(2)))
    return items


def _read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return ""


def done_when(text):
    """The Done-when clause of a backlog line, up to the first sentence end or results citation."""
    match = re.search(r"Done when (.+)", text)
    if not match:
        return None
    clause = re.split(r"\.\s+|\s+results/|\s+spec:", match.group(1), maxsplit=1)[0]
    return clause.strip(" .") or None


def clause_parts(clause):
    return [p.strip(" .") for p in clause.split(";") if p.strip(" .")] or [clause]


def run_tests(modules, root=ROOT, python=sys.executable):
    out = []
    for module in modules:
        if not module.startswith("tests."):
            out.append({"module": module, "passed": False, "ran": 0, "ids": [], "tail": "not under tests/"})
            continue
        proc = subprocess.run([python, "-m", "unittest", "-v", module], cwd=root, capture_output=True, text=True)
        text = proc.stdout + proc.stderr
        # 3.11+: "test_x (mod.Class.test_x) ... ok"; older: "test_x (mod.Class) ... ok"
        ids = [m.group(2) if m.group(2).endswith("." + m.group(1)) else f"{m.group(2)}.{m.group(1)}"
               for m in re.finditer(r"^(test\w*) \(([\w.]+)\)", text, re.M)]
        ran = re.search(r"Ran ([0-9]+) tests?", text)
        count = int(ran.group(1)) if ran else 0
        out.append({"module": module, "passed": proc.returncode == 0 and count > 0, "ran": count, "ids": ids,
                    "tail": "\n".join(text.strip().splitlines()[-4:])})
    return out


def code_changed(since, root=ROOT):
    names = _git(root, "diff", "--name-only", f"{since}..HEAD")
    if names is None:
        return None
    return [n for n in names.splitlines() if n.startswith(CODE_DIRS) and n.endswith(CODE_EXT)]


def claim_head(item, claims=CLAIMS):
    try:
        with open(os.path.join(claims, f"{item}.json")) as handle:
            return json.load(handle).get("head")
    except (OSError, json.JSONDecodeError):
        return None


def _results_keys(root, results):
    keys = {}
    for rel in results:
        try:
            with open(os.path.join(root, rel)) as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            keys[rel] = {k for k in data if k != "provenance"}
    return keys


def _proof_ok(proof, test_ids, keys):
    if proof in test_ids:
        return True
    if ":" in proof:
        rel, key = proof.rsplit(":", 1)
        return key in keys.get(rel, set())
    return any(proof in ks for ks in keys.values())


def _token(record):
    body = {k: v for k, v in record.items() if k != "token"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:10]


def check(item, results, tests, evidence, since=None, no_code=None, root=ROOT, backlog=BACKLOG,
          records=RECORDS, claims=CLAIMS, log=LOG, python=sys.executable):
    problems = []
    lines = backlog_items(_read(backlog)).get(item, [])
    if not lines:
        problems.append(f"{item} is not a '- {item}.' line in research/backlog.md")
    elif len(lines) > 1:
        problems.append(f"{item} appears {len(lines)} times in the backlog (lines {[n for n, _ in lines]}); one line per item")
    text = lines[0][1] if lines else ""
    head = claim_head(item, claims)
    if since and head and not _ancestor(root, since, head):
        problems.append(f"--since {since} is newer than the claim head {head}; use the commit work began from")
    since = since or head
    clause = done_when(text) if text else None
    if text and not clause:
        problems.append(f"{item} has no 'Done when' clause in the backlog; commit one, then claim")
    if clause and since:
        then = _git(root, "show", f"{since}:research/backlog.md") or ""
        then_lines = backlog_items(then).get(item, [])
        then_clause = done_when(then_lines[0][1]) if then_lines else None
        if then_clause != clause:
            problems.append(f"{item}: the Done-when clause was added or changed after {since}; commit the clause, then claim")
    parts = clause_parts(clause) if clause else []
    test_runs = run_tests(tests, root, python)
    test_ids = {i for t in test_runs for i in t["ids"]}
    problems.extend(f"{t['module']}: tests failed or ran none ({t['ran']} ran)" for t in test_runs if not t["passed"])
    if not tests:
        problems.append("no --tests module given; a done item has a test that runs under python3 -m unittest")
    if not results:
        problems.append("no --results file given; a done item has a provenance-stamped results file")
    checked = []
    for rel in results:
        path = os.path.join(root, rel)
        if item.lower() not in os.path.basename(rel).lower():
            problems.append(f"{rel} is not named for {item} (results/<date>_{item.lower()}_<name>.json)")
        if not os.path.exists(path):
            problems.append(f"results file {rel} does not exist")
            continue
        bad = verify_result(path, root)
        checked.append({"file": rel, "problems": bad})
        problems.extend(f"{rel}: {b}" for b in bad)
    keys = _results_keys(root, results)
    seen = set()
    for line in evidence:
        if not line.strip() or line.startswith("--") or ": " not in line or line in seen:
            problems.append(f"evidence {line!r} is empty, repeated or not '<part>: <proof>'")
            continue
        proof = line.split(": ", 1)[1].strip()
        if not _proof_ok(proof, test_ids, keys):
            problems.append(f"evidence proof {proof!r} is not a test that ran or a key in a cited results file")
            continue
        seen.add(line)
    if parts and len(seen) < len(parts):
        problems.append(f"the Done-when clause has {len(parts)} parts but {len(seen)} usable --evidence lines; parts: {parts}")
    changed = code_changed(since, root) if since else None
    if since and changed is None:
        problems.append(f"{since} is not a commit git knows")
    if no_code is not None:
        if len(no_code.strip()) < 30:
            problems.append("--no-code needs a sentence saying what was done instead of code")
    elif not since:
        problems.append("no claim head and no --since; take the claim before starting, or pass --since <commit work began from>")
    elif not changed:
        problems.append(f"no .py or .sh under scripts/ or regime_tester/ changed since {since}; tests, data and notes do not count")
    record = {"item": item, "checked_at": _stamp(), "head": _git(root, "rev-parse", "HEAD"), "done_when": clause,
              "parts": parts, "evidence": sorted(seen), "results": checked, "tests": test_runs,
              "code_changed_since": since, "code_files": changed, "no_code_reason": no_code,
              "problems": problems, "ok": not problems}
    record["token"] = _token(record)
    os.makedirs(records, exist_ok=True)
    out = os.path.join(records, f"{item}.json" if record["ok"] else f"{item}.fail.json")
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(record, handle, indent=1)
    os.replace(tmp, out)
    with open(log, "a") as handle:
        handle.write(json.dumps({k: record[k] for k in ("item", "checked_at", "head", "ok", "token")}) + "\n")
    return record


def done_line(record):
    return f"Done {record['checked_at'][:10]}. done_check {record['token']}."


def audit(root=ROOT, backlog=BACKLOG, records=RECORDS):
    """Violations: Done items without a passing, intact record; cited results that fail; duplicates; drift."""
    found, legacy = [], []
    violations = []

    def add(line):
        if line not in found:
            found.append(line)
    for item, lines in backlog_items(_read(backlog)).items():
        if len(lines) > 1:
            add(f"{item}: appears {len(lines)} times in the backlog (lines {[n for n, _ in lines]}); one line per item")
        for _, text in lines:
            clause = done_when(text)
            cite_text = text.replace(f"Done when {clause}", "") if clause else text
            mark, verdict = DONE_MARK.search(text), VERDICT_MARK.search(text)
            when = (mark.group(1) if mark and mark.group(1) else None) or (verdict.group(2) if verdict else None)
            latest = max(ANY_DATE.findall(text), default=None)
            if (mark or verdict) and when and when < GUARD_START:
                legacy.append(item)
                continue
            if latest is None or latest < GUARD_START:
                continue  # a line nobody has touched since the guards began is history, not a violation
            violations = found
            cited = sorted(set(CITATION.findall(cite_text)))
            for rel in cited:
                full = os.path.join(root, rel)
                bad = verify_result(full, root) if os.path.exists(full) else ["does not exist"]
                if bad:
                    add(f"{item}: cites {rel}, which {bad[0]}")
            if verdict and not mark and not cited:
                add(f"{item}: a {verdict.group(1).lower()} verdict with no results file cited")
            if not mark:
                if re.search(r"\bdone\b", text, re.I) and not re.search(r"not done|Done when|in progress|blocked", text, re.I):
                    add(f"{item}: status unparseable: says 'done' without a Done <date> mark")
                continue
            path = os.path.join(records, f"{item}.json")
            try:
                with open(path) as handle:
                    rec = json.load(handle)
            except (OSError, json.JSONDecodeError):
                add(f"{item}: marked Done in the backlog with no done_check record")
                continue
            if rec.get("token") != _token(rec) or not rec.get("ok") or not rec.get("results") or not rec.get("tests"):
                add(f"{item}: ops/done_checks/{item}.json was edited after done_check wrote it, or is incomplete")
                continue
            if rec["token"] not in text:
                add(f"{item}: backlog line does not carry the done_check token {rec['token']}")
            if rec.get("head") and not _ancestor(root, rec["head"], "HEAD"):
                add(f"{item}: done_check head {rec['head']} is not in this history")
            if clause and rec.get("done_when") != clause:
                add(f"{item}: the Done-when clause changed since done_check passed")
            for res in rec.get("results", []):
                bad = verify_result(os.path.join(root, res["file"]), root)
                if bad:
                    add(f"{item}: {res['file']} no longer verifies: {bad[0]}")
    violations = found
    if legacy:
        legacy = sorted(set(legacy))
        violations.append(f"{len(legacy)} items were marked done or given a verdict before {GUARD_START} without done_check "
                          f"({', '.join(legacy[:8])}{', ...' if len(legacy) > 8 else ''}); re-check any you still rely on")
    return violations


def report(item, root=ROOT, backlog=BACKLOG, records=RECORDS):
    """The run-report block, from the record on disk. Nothing in it is typed by the run."""
    rec = None
    for name in (f"{item}.json", f"{item}.fail.json"):
        try:
            with open(os.path.join(records, name)) as handle:
                rec = json.load(handle)
            break
        except (OSError, json.JSONDecodeError):
            continue
    lines = backlog_items(_read(backlog)).get(item, [])
    text = lines[0][1] if lines else ""
    head = _git(root, "rev-parse", "--short", "HEAD") or "none"
    if rec is None:
        status = "blocked" if re.search(r"\bBlocked\b", text) else "not started"
        return (f"{item}: {status}\ncommit {head}   test none   results none\ndone_check not run\ncode: none\n"
                f"left: every Done-when part\nnext: claim it and start at step 2\npushed: <fill from push.py>")
    ok = rec.get("ok") and rec.get("token") in text
    status = "done" if ok else ("partly done" if rec.get("results") or rec.get("code_files") else "not started")
    tests = "; ".join(f"{t['module']}: Ran {t['ran']} tests, {'OK' if t['passed'] else 'FAIL'}" for t in rec.get("tests", [])) or "none"
    results = ", ".join(r["file"] for r in rec.get("results", [])) or "none"
    dc = f"OK {rec['token']}" if rec.get("ok") else (f"FAIL: {rec['problems'][0]}" if rec.get("problems") else "not run")
    left = "none" if rec.get("ok") else "\n".join(f"  - {p}" for p in rec.get("problems", []))
    code = ", ".join(rec.get("code_files") or []) or "none"
    if rec.get("no_code_reason"):
        code += f" (no-code: {rec['no_code_reason']})"
    return (f"{item}: {status}\ncommit {head}   test {tests}   results {results}\ndone_check {dc}\ncode: {code}\n"
            f"left: {left}\nnext: <the one thing the next run does first>\npushed: <fill from push.py>")


def main(argv):
    parser = argparse.ArgumentParser(prog="done_check.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="op", required=True)
    c = sub.add_parser("check")
    c.add_argument("item")
    c.add_argument("--results", nargs="+", default=[])
    c.add_argument("--tests", nargs="+", default=[])
    c.add_argument("--evidence", action="append", default=[])
    c.add_argument("--since")
    c.add_argument("--no-code")
    sub.add_parser("audit")
    r = sub.add_parser("report")
    r.add_argument("item")
    args = parser.parse_args(argv[1:])
    if args.op == "audit":
        violations = audit()
        print("\n".join(violations) if violations else "done_check audit: no violations")
        return 1 if violations else 0
    if args.op == "report":
        print(report(args.item))
        return 0
    record = check(args.item, args.results, args.tests, args.evidence, args.since, args.no_code)
    if record["ok"]:
        print(f"DONE-CHECK OK {args.item} {record['token']}")
        print(f"paste into the {args.item} backlog line, exactly: {done_line(record)}")
        print("code changed: " + (", ".join(record["code_files"] or []) or f"none (no-code: {record['no_code_reason']})"))
        for line in record["evidence"]:
            print("evidence:", line)
        return 0
    print(f"DONE-CHECK FAIL {args.item}")
    for problem in record["problems"]:
        print(" -", problem)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
