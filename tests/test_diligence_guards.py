"""The guards: claims, provenance-stamped results, done_check, data_guard, procmgr disable.

Plain unittest: the box has no pytest. Each test builds a throwaway git repo.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import claim  # noqa: E402
import data_guard  # noqa: E402
import done_check  # noqa: E402
from regime_tester import results_io  # noqa: E402


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.STDOUT).strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)


def read(path):
    with open(path) as handle:
        return handle.read()


def make_repo():
    """A throwaway git repo with scripts/, tests/, results/, research/ and one commit."""
    root = tempfile.mkdtemp()
    for sub in ("scripts", "tests", "results", "research", "ops", "regime_tester", "data"):
        os.makedirs(os.path.join(root, sub))
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    write(os.path.join(root, "scripts", "writer.py"), "print('hi')\n")
    write(os.path.join(root, "data", "in.csv"), "date,close\n2026-01-01,1\n")
    write(os.path.join(root, "tests", "__init__.py"), "")
    write(os.path.join(root, "tests", "test_ok.py"), textwrap.dedent("""
        import unittest
        class T(unittest.TestCase):
            def test_true(self):
                self.assertTrue(True)
    """))
    write(os.path.join(root, "tests", "test_bad.py"), textwrap.dedent("""
        import unittest
        class T(unittest.TestCase):
            def test_false(self):
                self.assertTrue(False)
    """))
    write(os.path.join(root, "research", "backlog.md"),
          "# Backlog\n\n- A9. Fix the thing. Done when a test fails on the old file; the results file lists the count.\n"
          "- B2. No clause here at all.\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


class ResultsIO(unittest.TestCase):
    def setUp(self):
        self.root = make_repo()
        self.script = os.path.join(self.root, "scripts", "writer.py")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def stamped(self, name="thing", payload=None):
        return results_io.write_result(name, payload or {"n": 3}, inputs=["data/in.csv"], root=self.root, argv0=self.script)

    def test_stamped_result_verifies_and_hand_written_does_not(self):
        path = self.stamped()
        self.assertEqual(results_io.verify_result(path, self.root), [])
        data = json.loads(read(path))
        self.assertEqual(data["provenance"]["script"], "scripts/writer.py")
        self.assertEqual(data["provenance"]["inputs"][0]["kind"], "file")
        self.assertTrue(os.path.exists(os.path.join(self.root, "ops", "results_ledger.jsonl")))
        hand = os.path.join(self.root, "results", "2026-11-17_hand.json")
        write(hand, json.dumps({"n": 3}))
        self.assertTrue(any("by hand" in p for p in results_io.verify_result(hand, self.root)))

    def test_forged_stamp_and_edited_payload_fail(self):
        real = json.loads(read(self.stamped()))
        forged = os.path.join(self.root, "results", "2026-11-18_forged.json")
        write(forged, json.dumps({"n": 99999, "provenance": real["provenance"]}))
        problems = results_io.verify_result(forged, self.root)
        self.assertTrue(any("payload edited" in p for p in problems), problems)
        self.assertTrue(any("ledger" in p for p in problems), problems)
        empty = os.path.join(self.root, "results", "2026-11-18_empty.json")
        write(empty, json.dumps({"n": 1, "provenance": {"script": "", "commit": "", "written_at": "", "argv": []}}))
        problems = results_io.verify_result(empty, self.root)
        self.assertTrue(any("not a .py file under scripts/" in p for p in problems), problems)
        self.assertTrue(any("not in this repository's history" in p for p in problems), problems)

    def test_edit_run_revert_is_caught(self):
        original = read(self.script)
        write(self.script, original + "x = 1\n")
        path = self.stamped("edited")
        write(self.script, original)
        problems = results_io.verify_result(path, self.root)
        self.assertTrue(any("differs from the version committed" in p or "modified or untracked" in p for p in problems), problems)

    def test_refuses_dash_c_unittest_and_outside_scripts(self):
        with self.assertRaises(results_io.NotAScript):
            results_io.write_result("x", {}, inputs=["data/in.csv"], root=self.root, argv0="-c")
        outside = tempfile.NamedTemporaryFile(suffix=".py", delete=False).name
        with self.assertRaises(results_io.NotAScript):
            results_io.write_result("x", {}, inputs=["data/in.csv"], root=self.root, argv0=outside)
        with self.assertRaises(results_io.NotAScript):  # this very test runs under -m unittest
            results_io.write_result("x", {"a": 1}, inputs=["data/in.csv"], root=self.root)
        with self.assertRaises(ValueError):
            results_io.write_result("x", {"a": 1}, inputs=[], root=self.root, argv0=self.script)

    def test_argv0_override_cannot_point_at_untracked_or_non_script(self):
        new = os.path.join(self.root, "scripts", "new.py")
        write(new, "pass\n")
        path = results_io.write_result("y", {"a": 1}, inputs=["data"], root=self.root, argv0=new)
        self.assertTrue(any("modified or untracked" in p for p in results_io.verify_result(path, self.root)))
        with self.assertRaises(results_io.NotAScript):
            results_io.write_result("y", {"a": 1}, inputs=["data"], root=self.root,
                                    argv0=os.path.join(self.root, "research", "backlog.md"))

    def test_fixed_path_for_daemon_files(self):
        path = results_io.write_result("confirmations", {"rows": []}, inputs=["data"], root=self.root,
                                       argv0=self.script, path="results/sweeps/confirmations.json")
        self.assertTrue(path.endswith("results/sweeps/confirmations.json"))
        self.assertEqual(results_io.verify_result(path, self.root), [])


class Claims(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.claims = os.path.join(self.dir, "claims")
        self.log = os.path.join(self.dir, "claims.log")
        self.kw = dict(claims_dir=self.claims, log_path=self.log)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_second_taker_refused_and_release_needs_the_secret(self):
        code, rec = claim.take("A1", "cron", root=self.dir, **self.kw)
        self.assertEqual(code, 0)
        code, holder = claim.take("A1", "chat", root=self.dir, **self.kw)
        self.assertEqual(code, claim.HELD)
        self.assertEqual(holder["owner"], "cron")
        self.assertEqual(claim.release("A1", "cron", secret="wrong", **self.kw)[0], claim.HELD)
        self.assertEqual(claim.release("A1", "cron", secret=None, **self.kw)[0], claim.HELD)
        self.assertEqual(claim.touch("A1", "cron", secret=rec["secret"], **self.kw)[0], 0)
        self.assertEqual(claim.release("A1", "cron", secret=rec["secret"], **self.kw)[0], 0)
        self.assertEqual(claim.status(self.claims), [])
        self.assertIn("HELD A1 wanted by chat", read(self.log))

    def test_force_needs_reason_and_is_reported(self):
        claim.take("A1", "cron", root=self.dir, **self.kw)
        with self.assertRaises(SystemExit):
            claim.release("A1", "chat", force=True, reason="", **self.kw)
        self.assertEqual(claim.release("A1", "chat", force=True, reason="cron died at 03:10, see log", **self.kw)[0], 0)
        events = claim.recent_events(self.log)
        self.assertEqual(len(events), 1)
        self.assertIn("(forced)", events[0])

    def test_expired_claim_takeover_keeps_original_head_and_is_exclusive(self):
        claim.take("A1", "cron", root=self.dir, **self.kw)
        rec = claim.read("A1", self.claims)
        rec["touched_at"] = "2020-01-01T00:00:00Z"
        rec["head"] = "abc1234"
        write(os.path.join(self.claims, "A1.json"), json.dumps(rec))
        code, record = claim.take("A1", "chat", root=self.dir, **self.kw)
        self.assertEqual(code, 0)
        self.assertEqual(record["took_over"]["reason"], "took over expired claim")
        self.assertEqual(record["head"], "abc1234")
        self.assertEqual(claim.take("A1", "cron", root=self.dir, **self.kw)[0], claim.HELD)
        self.assertIn("TAKEOVER A1 by chat", read(self.log))

    def test_steal_needs_reason_and_is_reported(self):
        claim.take("A1", "cron", root=self.dir, **self.kw)
        with self.assertRaises(SystemExit):
            claim.take("A1", "chat", steal=True, root=self.dir, **self.kw)
        code, _ = claim.take("A1", "chat", steal=True, reason="operator: cron run hung on A1", root=self.dir, **self.kw)
        self.assertEqual(code, 0)
        self.assertTrue(any("stole live claim" in e for e in claim.recent_events(self.log)))

    def test_item_names_and_ttl_are_restricted_and_corrupt_claims_expire(self):
        for bad in ("../etc", "А1", "a1", "A1 "):
            with self.assertRaises(SystemExit):
                claim.take(bad, "cron", root=self.dir, **self.kw)
        for ttl in (0, -1, 48, float("nan")):
            with self.assertRaises(SystemExit):
                claim.take("A2", "cron", ttl_hours=ttl, root=self.dir, **self.kw)
        os.makedirs(self.claims, exist_ok=True)
        write(os.path.join(self.claims, "A7.json"), "{bad")
        rows = claim.status(self.claims)
        self.assertTrue(rows[0]["corrupt"] and rows[0]["expired"])
        self.assertEqual(claim.take("A7", "cron", root=self.dir, **self.kw)[0], 0)


class DoneCheck(unittest.TestCase):
    def setUp(self):
        self.root = make_repo()
        self.backlog = os.path.join(self.root, "research", "backlog.md")
        self.records = os.path.join(self.root, "ops", "done_checks")
        self.claims = os.path.join(self.root, "ops", "claims")
        self.log = os.path.join(self.root, "ops", "done_checks.log")
        self.base = git(self.root, "rev-parse", "HEAD")
        self.script = os.path.join(self.root, "scripts", "writer.py")
        os.makedirs(self.claims)
        write(os.path.join(self.claims, "A9.json"), json.dumps({"item": "A9", "owner": "cron", "head": self.base}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def stamped(self, name="a9_counts", payload=None):
        path = results_io.write_result(name, payload or {"count": 1}, inputs=["data/in.csv"], root=self.root, argv0=self.script)
        return os.path.relpath(path, self.root)

    def commit_code(self):
        write(os.path.join(self.root, "scripts", "fix.py"), "x = 1\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fix")

    def run_check(self, item="A9", **kw):
        args = dict(results=[], tests=["tests.test_ok"], evidence=None, since=None, no_code=None, root=self.root,
                    backlog=self.backlog, records=self.records, claims=self.claims, log=self.log)
        args.update(kw)
        if args["evidence"] is None:
            first = args["results"][0] if args["results"] else "results/none.json"
            args["evidence"] = ["old file fails: tests.test_ok.T.test_true", f"lists the count: {first}:count"]
        return done_check.check(item, **args)

    def aud(self):
        return done_check.audit(self.root, self.backlog, self.records)

    def test_a_multiline_verbose_id_keeps_the_dotted_module(self):
        """3.11 prints the docstring on the next line, so the id ends at ')'.

        A pattern that also demands '... ok' on the same line matches nothing
        once the module name contains a dot, and every evidence line then fails.
        """
        text = ("test_true (tests.test_ok.T.test_true)\n"
                "A later reader must see the real store. ... ok\n"
                "\n----------------------------------------------------------------------\n"
                "Ran 1 test in 0.001s\n\nOK\n")
        ids = [m.group(2) if m.group(2).endswith("." + m.group(1)) else f"{m.group(2)}.{m.group(1)}"
               for m in done_check.re.finditer(r"^(test\w*) \(([\w.]+)\)", text, done_check.re.M)]
        self.assertEqual(ids, ["tests.test_ok.T.test_true"])

    def test_passes_with_stamped_results_passing_tests_code_and_evidence(self):
        self.commit_code()
        rec = self.run_check(results=[self.stamped()])
        self.assertTrue(rec["ok"], rec["problems"])
        self.assertEqual(rec["parts"], ["a test fails on the old file", "the results file lists the count"])
        self.assertTrue(os.path.exists(os.path.join(self.records, "A9.json")))
        self.assertIn('"ok": true', read(self.log))
        self.assertEqual(done_check.done_line(rec), f"Done {rec['checked_at'][:10]}. done_check {rec['token']}.")
        block = done_check.report("A9", self.root, self.backlog, self.records)
        self.assertIn("A9: partly done", block)  # token not yet in the backlog line
        self.assertIn("scripts/fix.py", block)

    def test_hand_written_results_and_wrong_name_fail(self):
        self.commit_code()
        write(os.path.join(self.root, "results", "2026-11-17_a9_hand.json"), json.dumps({"count": 1}))
        rec = self.run_check(results=["results/2026-11-17_a9_hand.json"])
        self.assertTrue(any("by hand" in p for p in rec["problems"]), rec["problems"])
        rec = self.run_check(results=[self.stamped("other_name")])
        self.assertTrue(any("is not named for A9" in p for p in rec["problems"]), rec["problems"])

    def test_failing_or_empty_tests_junk_evidence_and_no_code_fail(self):
        res = self.stamped()
        rec = self.run_check(results=[res], tests=["tests.test_bad", "json"], evidence=["x", "a: b", "a: b"])
        joined = " | ".join(rec["problems"])
        self.assertIn("tests.test_bad: tests failed", joined)
        self.assertIn("json: tests failed or ran none", joined)
        self.assertIn("evidence 'x' is empty, repeated or not", joined)
        self.assertIn("proof 'b' is not a test that ran", joined)
        self.assertIn("2 parts but 0 usable", joined)
        self.assertIn("no .py or .sh under scripts/ or regime_tester/ changed", joined)
        self.assertTrue(os.path.exists(os.path.join(self.records, "A9.fail.json")))
        self.assertFalse(os.path.exists(os.path.join(self.records, "A9.json")))
        rec = self.run_check(results=[res], no_code="short")
        self.assertTrue(any("--no-code needs a sentence" in p for p in rec["problems"]))
        rec = self.run_check(results=[res], no_code="A9 needed no code: the clause only asks for the results file and a test.")
        self.assertTrue(rec["ok"], rec["problems"])

    def test_since_newer_than_claim_head_is_refused_and_older_ancestor_allowed(self):
        self.commit_code()
        newer = git(self.root, "rev-parse", "HEAD")
        rec = self.run_check(results=[self.stamped()], since=newer)
        self.assertTrue(any("newer than the claim head" in p for p in rec["problems"]), rec["problems"])
        rec = self.run_check(results=[self.stamped("a9_b")], since=self.base)
        self.assertTrue(rec["ok"], rec["problems"])

    def test_clause_added_after_the_claim_and_duplicate_items_fail(self):
        self.commit_code()
        write(self.backlog, read(self.backlog).replace("- B2. No clause here at all.", "- B2. No clause here at all. Done when it exists."))
        write(os.path.join(self.claims, "B2.json"), json.dumps({"item": "B2", "owner": "cron", "head": self.base}))
        rec = self.run_check("B2", results=[self.stamped("b2_x")], evidence=["it exists: tests.test_ok.T.test_true"])
        self.assertTrue(any("added or changed after" in p for p in rec["problems"]), rec["problems"])
        write(self.backlog, read(self.backlog) + "  - A9. again. Done when x.\n")
        rec = self.run_check(results=[self.stamped("a9_c")])
        self.assertTrue(any("appears 2 times" in p for p in rec["problems"]), rec["problems"])

    def test_audit_catches_missing_record_edited_record_wrong_token_and_bad_citations(self):
        write(os.path.join(self.root, "results", "2026-11-17_a9_hand.json"), json.dumps({"count": 1}))
        base_text = read(self.backlog)
        write(self.backlog, base_text.replace("- A9. Fix the thing.", "- A9. Fix the thing. Done 2026-11-18. results/2026-11-17_a9_hand.json."))
        joined = " | ".join(self.aud())
        self.assertIn("no done_check record", joined)
        self.assertIn("cites results/2026-11-17_a9_hand.json, which no provenance", joined)
        os.makedirs(self.records, exist_ok=True)
        write(os.path.join(self.records, "A9.json"), json.dumps({"ok": True}))
        self.assertTrue(any("edited after done_check wrote it" in v for v in self.aud()))
        self.commit_code()
        rec = self.run_check(results=[self.stamped()])
        self.assertTrue(rec["ok"], rec["problems"])
        write(self.backlog, base_text.replace("- A9. Fix the thing.", f"- A9. Fix the thing. {done_check.done_line(rec)}"))
        self.assertEqual(self.aud(), [])
        write(self.backlog, base_text.replace("- A9. Fix the thing.", "- A9. Fix the thing. Done 2026-11-18. done_check 0000000000."))
        self.assertTrue(any("does not carry the done_check token" in v for v in self.aud()))
        write(self.backlog, base_text.replace("- A9. Fix the thing.", f"- A9. Fix the thing. Done 2026-11-18, done_check {rec['token']}."))
        self.assertEqual(self.aud(), [])  # the comma form is still a Done mark, and the token is present

    def test_audit_ignores_not_done_and_done_when_but_checks_verdicts_and_legacy(self):
        write(self.backlog, read(self.backlog).replace(
            "- B2. No clause here at all.",
            "- B2. In progress 2026-11-18, not done. Done when it is.\n- C3. Rejected 2026-11-18. No file cited.\n"
            "- C4. Insufficient 2026-11-18. results/2026-11-17_c4_hand.json.\n- E1. Old item. Done 2026-11-01.\n"
            "- S7. Both runs done, 2026-11-18.\n- S2. Old line, no date. results/2026-11-05_missing.json.\n- A7. Done per test with its results file.\n"))
        write(os.path.join(self.root, "results", "2026-11-17_c4_hand.json"), json.dumps({"n": 1}))
        joined = " | ".join(self.aud())
        self.assertNotIn("B2", joined)
        self.assertIn("C3: a rejected verdict with no results file cited", joined)
        self.assertIn("C4: cites results/2026-11-17_c4_hand.json, which no provenance", joined)
        self.assertIn("1 items were marked done or given a verdict before 2026-11-18", joined)
        self.assertIn("S7: status unparseable", joined)
        self.assertNotIn("S2", joined)
        self.assertNotIn("A7", joined)


class DataGuard(unittest.TestCase):
    def setUp(self):
        self.root = make_repo()
        self.manifests = os.path.join(self.root, "ops", "manifests")
        self.script = os.path.join(self.root, "scripts", "writer.py")
        self.panel = os.path.join(self.root, "data", "panel")
        for name in ("a.csv", "b.csv", "c.csv", "sub/d.csv"):
            write(os.path.join(self.panel, name), "date,close\n2026-01-01,1\n2026-01-02,2\n")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_check_reports_removed_shrunk_and_rewritten_but_not_grown(self):
        data_guard.snapshot("data/panel", self.root, self.manifests)
        self.assertEqual(data_guard.check("data/panel", self.root, self.manifests), [])
        os.remove(os.path.join(self.panel, "sub", "d.csv"))
        write(os.path.join(self.panel, "c.csv"), "x")
        write(os.path.join(self.panel, "a.csv"), "date,close\n2026-01-02,2\n2026-01-01,1\n")  # same size, rows reversed
        with open(os.path.join(self.panel, "b.csv"), "a") as handle:
            handle.write("2026-01-03,3\n")  # grew: a puller appended
        problems = data_guard.check("data/panel", self.root, self.manifests)
        self.assertEqual(len(problems), 3, problems)
        self.assertIn("sub/d.csv", problems[0])
        self.assertIn("shrank", problems[1])
        self.assertIn("rewritten in place", problems[2])
        self.assertIn("a.csv", problems[2])

    def test_snapshot_after_a_loss_is_refused_unless_declared_and_logged(self):
        data_guard.snapshot("data/panel", self.root, self.manifests)
        os.remove(os.path.join(self.panel, "b.csv"))
        with self.assertRaises(SystemExit):
            data_guard.snapshot("data/panel", self.root, self.manifests)
        self.assertEqual(len(data_guard.check("data/panel", self.root, self.manifests)), 1)
        with self.assertRaises(SystemExit):  # declared count without an item in the reason
            data_guard.snapshot("data/panel", self.root, self.manifests, note="oops", accept_removed=1)
        data_guard.snapshot("data/panel", self.root, self.manifests, note="A1: b.csv was a duplicate venue", accept_removed=1)
        self.assertEqual(data_guard.check("data/panel", self.root, self.manifests), [])
        losses = data_guard.recent_losses(self.manifests)
        self.assertEqual(len(losses), 1)
        self.assertIn("removed 1", losses[0])
        self.assertTrue(any(n.endswith(".prev") for n in os.listdir(self.manifests)))

    def test_swap_refuses_removals_shrinkage_empty_source_nesting_and_keeps_previous(self):
        new = os.path.join(self.root, "data", "panel_new")
        for name in ("a.csv", "b.csv", "sub/d.csv"):
            write(os.path.join(new, name), "date,close\n2026-01-01,1\n2026-01-02,2\n2026-01-03,3\n")
        write(os.path.join(new, "b.csv"), "x")
        with self.assertRaises(SystemExit):
            data_guard.swap("data/panel_new", "data/panel", "A1 rewrite test", 0, 0, self.root, self.manifests, self.script)
        with self.assertRaises(SystemExit):
            data_guard.swap("data/panel_new", "data/panel", "rewrite without an item id", 1, 1, self.root, self.manifests, self.script)
        with self.assertRaises(SystemExit):
            data_guard.swap("data/panel/sub", "data/panel", "A1: nested", 0, 0, self.root, self.manifests, self.script)
        os.makedirs(os.path.join(self.root, "data", "empty"))
        with self.assertRaises(SystemExit):
            data_guard.swap("data/empty", "data/panel", "A1: wipe it", 4, 0, self.root, self.manifests, self.script)
        self.assertTrue(os.path.isdir(new) and os.path.isdir(self.panel))
        rec = data_guard.swap("data/panel_new", "data/panel", "A1 rewrite test: c dropped on purpose, b truncated", 1, 1,
                              self.root, self.manifests, self.script)
        self.assertEqual((rec["diff_counts"]["removed"], rec["diff_counts"]["shrunk"]), (1, 1))
        prev = os.path.join(self.root, rec["swap"]["kept_previous_as"])
        self.assertTrue(os.path.isfile(os.path.join(prev, "c.csv")), "the old directory is kept, not deleted")
        self.assertFalse(os.path.exists(new))
        self.assertEqual(results_io.verify_result(os.path.join(self.root, rec["results_file"]), self.root), [])
        self.assertEqual(data_guard.check("data/panel", self.root, self.manifests), [])
        self.assertTrue(any("swap" in line for line in data_guard.recent_losses(self.manifests)))


class ProcmgrDisable(unittest.TestCase):
    """procmgr reads ROOT from cwd, so run it as a subprocess in a temp dir."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "scripts"))
        write(os.path.join(self.dir, "d.py"), "import time\ntime.sleep(30)\n")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def pm(self, *args):
        return subprocess.run([sys.executable, os.path.join(REPO, "scripts", "procmgr.py"), *args], cwd=self.dir,
                              capture_output=True, text=True, env=self.env)

    def test_disabled_daemon_and_its_command_stay_off_until_enabled_with_a_reason(self):
        self.pm("register", "sleeper", "--", sys.executable, "d.py")
        self.assertEqual(self.pm("disable", "sleeper", "short").returncode, 2)
        out = self.pm("disable", "sleeper", "review: keep off until A2 passes")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        for args in (("start", "sleeper"), ("restart", "sleeper"), ("start", "alias", "--", sys.executable, "d.py")):
            out = self.pm(*args)
            self.assertEqual(out.returncode, 3, (args, out.stdout, out.stderr))
            self.assertIn("disabled", out.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "ops", "pids", "sleeper.pid")))
        self.assertNotIn("alias", json.loads(read(os.path.join(self.dir, "ops", "daemons.json"))))
        out = self.pm("supervise")
        self.assertIn("skipped disabled ['sleeper']", out.stdout)
        status = json.loads(self.pm("status", "sleeper").stdout.strip().splitlines()[-1])
        self.assertTrue(status["disabled"])
        self.assertEqual(self.pm("enable", "sleeper", "x").returncode, 2)
        self.assertEqual(self.pm("enable", "sleeper", "A2 two-cell test passed in 1a2b3c4").returncode, 0)
        self.assertFalse(json.loads(self.pm("status", "sleeper").stdout.strip().splitlines()[-1])["disabled"])
        log = read(os.path.join(self.dir, "ops", "daemons.log"))
        self.assertIn("DISABLE sleeper", log)
        self.assertIn("ENABLE sleeper", log)


if __name__ == "__main__":
    unittest.main()
