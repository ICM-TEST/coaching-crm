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
            "--invoice-start", "490", "--google", "riley.drive@example.test")
        me = frontmatter(self.root / "coach-riley/riley.me.txt")
        self.assertEqual((me["coach_number"], me["code"], me["phone"], me["email"], me["invoice_start"], me["role"]),
                         ("02", "RI", "+27820000002", "riley@example.test", "490", "coach"))
        self.assertTrue((self.root / "coach-riley/invoice-lists").is_dir())

        # the Project instruction names exactly who this Claude works for, and its folder
        (self.root / "factory/business.txt").write_text("trading_name: Example Coaching Co\n")
        (self.root / "hub/morgan.me.txt").write_text("name: Morgan Head\nslug: morgan\nrole: head-coach\n")
        out = run(self.root, "instructions", "riley")
        for expected in ("You are the Claude for Riley Coach, coach 02 at Example Coaching Co", "coach-riley/ and factory/ in Google Drive",
                         "If you can open hub/ or any other coach's folder", "stop"):
            self.assertIn(expected, out)
        self.assertNotIn("Morgan", out)
        run(self.root, "instructions", "head-coach", ok=(1,))          # the head coach's names only the role
        run(self.root, "instructions", "nobody", ok=(1,))
        self.assertEqual([c["google_account"] for c in read_table(self.root / "hub/coaches.csv")],
                         ["morgan@example.test", "riley.drive@example.test"])           # defaults to the invoice email

        # the step-by-step texts, filled in: nothing left to guess, no placeholder left over
        share, welcome, unshare = (run(self.root, part, "riley") for part in ("share", "welcome", "unshare"))
        for text in (share, welcome, unshare):
            self.assertNotRegex(text, r"\{[a-z]+\}")
            self.assertIn("riley.drive@example.test", text)
            self.assertIn("coach-riley", text)
        self.assertIn("Contributor", share)
        self.assertIn("Never add Riley as a member of the whole shared drive", share)
        self.assertIn("You are the Claude for Riley Coach, coach 02 at Example Coaching Co", welcome)
        self.assertIn("send Morgan a screenshot", welcome)
        self.assertIn("https://github.com/ICM-TEST/coaching-crm", welcome)
        self.assertIn("five folders", unshare)
        run(self.root, "welcome", "nobody", ok=(1,))

        append_rows(self.root / "hub/clients.csv", ["id", "name", "phone", "email", "status", "coach", "since", "notes"],
                    [{"id": "C0001", "name": "Ann Example", "phone": "+27820000009", "status": "active", "coach": "riley"}])
        out = run(self.root, "list")
        self.assertRegex(out, r"02\s+Riley Coach\s+\+27820000002\s+riley@example.test\s+1\s+yes")

        out = run(self.root, "leave", "riley")
        self.assertIn("1 client(s) are now unallocated", out)
        self.assertIn("C0001  Ann Example", out)
        ann = read_table(self.root / "hub/clients.csv")[0]
        self.assertEqual((ann["status"], ann["coach"]), ("unallocated", "riley"))      # the last coach stays visible
        self.assertEqual(read_table(self.root / "hub/client-history.csv")[-1]["change"], "coach riley → unallocated")
        self.assertEqual(read_table(self.root / "coach-riley/clients.csv"), [], "a coach who leaves sees no clients")
        self.assertEqual([c["active"] for c in read_table(self.root / "hub/coaches.csv")], ["yes", "no"])
        self.assertTrue((self.root / "coach-riley/riley.me.txt").exists(), "a coach who leaves keeps their folder")

        out = run(self.root, "add", "--name", "Riley Second", "--email", "q2@example.test")
        self.assertIn("as coach 03", out)                          # 02 is never reused
        self.assertIn("folder coach-riley2/", out)
        self.assertNotEqual(frontmatter(self.root / "coach-riley2/riley2.me.txt")["code"], "RI")

    def test_a_changed_phone_reaches_the_coach(self):
        run(self.root, "add", "--name", "Riley Coach", "--phone", "+27820000002")
        path = self.root / "hub/coaches.csv"
        path.write_text(path.read_text().replace("+27820000002", "+27829999999"))
        subprocess.run([sys.executable, "scripts/build_lists.py", "--root", str(self.root), "coach-clients"],
                       cwd=REPO, check=True, capture_output=True)
        self.assertEqual(frontmatter(self.root / "coach-riley/riley.me.txt")["phone"], "+27829999999")


if __name__ == "__main__":
    unittest.main(verbosity=2)
