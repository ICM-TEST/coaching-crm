#!/usr/bin/env python3
"""The head coach's list of coaches: numbering, the generated me Doc, leaving. Made-up data.

Run from the repo root:  python3 tools/tests/test_coaches.py
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent / "workspace"
sys.path.insert(0, str(REPO / "scripts"))
from crm.common import append_rows, frontmatter, read_table  # noqa: E402


def run(root, *args, ok=(0,)):
    p = subprocess.run([sys.executable, "scripts/coaches.py", "--root", str(root), *args], cwd=REPO,
                       capture_output=True, text=True)
    if p.returncode not in ok:
        raise AssertionError(f"{args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p.stdout


class Coaches(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "drive"
        shutil.copytree(REPO / "_templates" / "drive", self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_numbers_list_and_leaving(self):
        out = run(self.root, "add", "--name", "Morgan Head", "--phone", "+27820000001", "--email", "morgan@example.test",
                  "--invoice-start", "1200")
        self.assertIn("Added Morgan Head as coach 01", out)
        run(self.root, "add", "--name", "Riley Coach", "--phone", "+27820000002", "--email", "riley@example.test",
            "--invoice-start", "490")
        me = frontmatter(self.root / "coach-riley/me.txt")
        self.assertEqual((me["coach_number"], me["code"], me["phone"], me["email"], me["invoice_start"], me["role"]),
                         ("02", "RI", "+27820000002", "riley@example.test", "490", "coach"))
        self.assertTrue((self.root / "coach-riley/invoice-lists").is_dir())

        # the Project instruction names exactly who this Claude works for, and its folder
        (self.root / "factory/business.txt").write_text("trading_name: Example Coaching Co\n")
        (self.root / "hub/me.txt").write_text("name: Morgan Head\nslug: morgan\nrole: head-coach\n")
        out = run(self.root, "instructions", "riley")
        for expected in ("You are the Claude for Riley Coach, coach 02 at Example Coaching Co", "Your folder is coach-riley/",
                         "If you can open hub/ or any other coach's folder", "stop"):
            self.assertIn(expected, out)
        self.assertNotIn("Morgan", out)
        out = run(self.root, "instructions", "head-coach")
        self.assertIn("You are the Claude for Morgan Head, the head coach", out)
        self.assertIn("coach-morgan/", out)
        run(self.root, "instructions", "nobody", ok=(1,))

        append_rows(self.root / "hub/clients.csv", ["id", "name", "phone", "email", "status", "coach", "since", "notes"],
                    [{"id": "C0001", "name": "Ann Example", "phone": "+27820000009", "status": "active", "coach": "riley"}])
        out = run(self.root, "list")
        self.assertRegex(out, r"02\s+Riley Coach\s+\+27820000002\s+riley@example.test\s+1\s+yes")

        out = run(self.root, "leave", "riley")
        self.assertIn("reassign their 1 active client(s)", out)
        self.assertEqual([c["active"] for c in read_table(self.root / "hub/coaches.csv")], ["yes", "no"])
        self.assertTrue((self.root / "coach-riley/me.txt").exists(), "a coach who leaves keeps their folder")

        out = run(self.root, "add", "--name", "Riley Second", "--email", "q2@example.test")
        self.assertIn("as coach 03", out)                          # 02 is never reused
        self.assertIn("folder coach-riley2/", out)
        self.assertNotEqual(frontmatter(self.root / "coach-riley2/me.txt")["code"], "RI")

    def test_a_changed_phone_reaches_the_coach(self):
        run(self.root, "add", "--name", "Riley Coach", "--phone", "+27820000002")
        path = self.root / "hub/coaches.csv"
        path.write_text(path.read_text().replace("+27820000002", "+27829999999"))
        subprocess.run([sys.executable, "scripts/build_lists.py", "--root", str(self.root), "coach-clients"],
                       cwd=REPO, check=True, capture_output=True)
        self.assertEqual(frontmatter(self.root / "coach-riley/me.txt")["phone"], "+27829999999")


if __name__ == "__main__":
    unittest.main(verbosity=2)
