#!/usr/bin/env python3
"""First-run setup (workspace/setup/SKILL.md) on made-up data: from an empty folder to a plan the head coach may carry out.

Run from the repo root:  python3 tools/tests/test_setup.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


class Setup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.w = self.tmp / "work"
        self.w.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_(self, script, *a):
        p = subprocess.run([sys.executable, "-B", f"scripts/{script}", *a], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def build(self):
        self.run_("sync.py", "snapshot", str(self.w))
        shutil.copytree(REPO / "_templates/drive", self.w, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("coach-template", "fonts", ".DS_Store"))
        (self.w / "hub/morgan.me.txt").write_text("name: Morgan Test\nslug: morgan\nrole: head-coach\n")
        for name, phone, start in (("Morgan Test", "0820000001", "100"), ("Riley Test", "+27 82 000 0002", "490")):
            self.run_("coaches.py", "--root", str(self.w), "add", "--name", name, "--phone", phone,
                      "--email", "x@example.test", "--invoice-start", start)
        return json.loads(self.run_("sync.py", "plan", str(self.w), "--role", "head-coach", "--json"))

    def test_plan_is_allowed_and_builds_the_drive(self):
        ops = self.build()
        kinds = {o["op"] for o in ops}
        self.assertEqual(kinds, {"create_folder", "create_sheet", "create_doc"})         # nothing to upload: no fonts
        paths = {o["path"] for o in ops}
        for expected in ("hub", "factory", "_archive", "hub/recon", "factory/invoice-template", "coach-riley/invoice-lists",
                         "coach-riley/invoices", "coach-riley/pops", "hub/clients", "hub/coaches", "hub/morgan.me",
                         "factory/release", "coach-riley/riley.me", "coach-riley/clients", "coach-riley/unpaid",
                         "factory/client-form", "hub/bank/lines"):
            self.assertIn(expected, paths)
        self.assertFalse({"hub/me", "coach-riley/me", "hub/settings"} & paths, "every .me Doc is named after its person")
        self.assertFalse([p for p in paths if p.endswith(".ttf")])
        folders = [o["path"] for o in ops if o["op"] == "create_folder"]
        for p in folders:                                                                # parents before children
            if "/" in p:
                self.assertLess(folders.index(p.rsplit("/", 1)[0]), folders.index(p))
        coaches = next(o for o in ops if o["path"] == "hub/coaches")["values"]
        self.assertTrue(any("'+27 82 000 0002" in r for r in coaches), "phones go up protected")

    def test_coach_instruction_is_short_and_names_the_person(self):
        self.build()
        out = self.run_("coaches.py", "--root", str(self.w), "instructions", "riley")
        self.assertIn("Riley Test, coach 02", out)
        self.assertIn("workspace/CLAUDE.md", out)
        self.assertIn("coach-riley/", out)
        self.assertNotIn('"work"', out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
