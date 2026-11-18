"""The diligence skill is pinned: changing SKILL.md without updating SHA256 fails the suite.

That makes any edit to the procedure a visible, two-file commit, and lets the
health check tell when the installed copy drifts from the committed one.
"""

import hashlib
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(HERE), "skills", "diligence", "SKILL.md")
PIN = os.path.join(os.path.dirname(HERE), "skills", "diligence", "SHA256")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class SkillPinned(unittest.TestCase):
    def test_skill_matches_pin(self):
        self.assertTrue(os.path.exists(SKILL), "skills/diligence/SKILL.md is missing")
        self.assertTrue(os.path.exists(PIN), "skills/diligence/SHA256 is missing")
        with open(PIN) as handle:
            pinned = handle.read().split()[0]
        self.assertEqual(sha256(SKILL), pinned,
                         "SKILL.md changed. If that was intended, update skills/diligence/SHA256 in the same "
                         "commit and say why in the message; then re-run skills/diligence/install.sh")

    def test_installed_copy_matches_when_present(self):
        dest = os.path.join(os.environ.get("HERMES_SKILLS_DIR", os.path.expanduser("~/.hermes/skills")),
                            "research", "diligence", "SKILL.md")
        if not os.path.exists(dest):
            self.skipTest("skill not installed on this machine")
        self.assertEqual(sha256(dest), sha256(SKILL), "installed skill differs from the committed one; re-run install.sh")


if __name__ == "__main__":
    unittest.main()
