#!/usr/bin/env python3
"""The head coach's client list: details of their own, and bringing in a list the business already has.

Run from the repo root:  python3 tools/tests/test_clients.py
Every name, number and amount here is invented.
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent / "workspace"
sys.path.insert(0, str(REPO / "scripts"))
from crm.common import read_table  # noqa: E402


def run(root, script, *args, ok=(0,)):
    p = subprocess.run([sys.executable, "-B", f"scripts/{script}", "--root", str(root), *args], cwd=REPO,
                       capture_output=True, text=True, env=dict(os.environ, CRM_TODAY="2026-11-09"))
    if p.returncode not in ok:
        raise AssertionError(f"{args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p.stdout


class Clients(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "work"
        shutil.copytree(REPO / "_templates" / "drive", self.root)
        shutil.rmtree(self.root / "coach-template")
        (self.root / "hub/alex.me.txt").write_text("name: Alex Head\nslug: alex\nrole: head-coach\n")
        for name in ("Alex Head", "Jordan Coach"):
            run(self.root, "coaches.py", "add", "--name", name, "--phone", "0820000001", "--email", "x@example.test")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def current_list(self, header, rows):
        path = self.tmp / "current.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        return str(path)

    def test_details_of_the_head_coachs_own(self):
        out = run(self.root, "clients.py", "details", "--add", "Who pays", "Level")
        self.assertIn("Added: Who pays, Level", out)
        self.assertIn("own details: Who pays, Level", out)
        run(self.root, "clients.py", "details", "--add", "level", ok=(1,))            # already kept
        self.assertTrue((self.root / "hub/clients.csv").read_text().rstrip().endswith("notes,Who pays,Level"))

    def test_import_an_existing_list(self):
        run(self.root, "clients.py", "details", "--add", "Who pays")
        file = self.current_list(["name", "phone", "email", "coach", "notes", "Who pays"], [
            ["Ann Example", "0830000001", "ann@example.test", "Jordan", "", "B Example"],     # coach by first name
            ["Ben Example", "0830000001", "", "Alex Head", "", ""],                            # same phone: family?
            ["Cy Example", "", "cy@example.test", "", "joined 2024", ""],                      # no coach yet, no phone
        ])
        out = run(self.root, "clients.py", "import", file, "--dry-run")
        self.assertIn("3 client(s) ready to add", out)
        self.assertIn("Jordan Coach: 1", out)
        self.assertIn("unallocated (no coach yet): 1", out)
        self.assertIn("same phone as Ann Example", out)
        self.assertIn("Cy Example): no phone", out)
        self.assertEqual(read_table(self.root / "hub/clients.csv"), [], "a dry run adds nothing")

        run(self.root, "clients.py", "import", file)
        rows = {r["name"]: r for r in read_table(self.root / "hub/clients.csv")}
        self.assertEqual([rows[n]["id"] for n in ("Ann Example", "Ben Example", "Cy Example")], ["C0001", "C0002", "C0003"])
        self.assertEqual((rows["Ann Example"]["coach"], rows["Ann Example"]["status"]), ("jordan", "active"))
        self.assertEqual((rows["Cy Example"]["coach"], rows["Cy Example"]["status"]), ("", "unallocated"))
        self.assertEqual(rows["Ann Example"]["Who pays"], "B Example")
        self.assertEqual(len(read_table(self.root / "hub/client-history.csv")), 3)
        mine = read_table(self.root / "coach-jordan/clients.csv")
        self.assertEqual([r["name"] for r in mine], ["Ann Example"])
        self.assertNotIn("Who pays", mine[0], "the head coach's own details never reach a coach")
        self.assertNotIn("B Example", (self.root / "coach-jordan/clients.csv").read_text())

        out = run(self.root, "clients.py", "import", file, ok=(1,))                   # the same list twice
        self.assertIn("already in the list", out)
        self.assertEqual(len(read_table(self.root / "hub/clients.csv")), 3)

    def test_what_the_list_doesnt_keep_is_refused(self):
        file = self.current_list(["name", "coach", "Shoe size"], [["Dee Example", "Nobody"]])
        out = run(self.root, "clients.py", "import", file, ok=(1,))
        self.assertIn("columns the list doesn't keep: Shoe size", out)
        self.assertIn("no active coach called 'Nobody'", out)
        self.assertEqual(read_table(self.root / "hub/clients.csv"), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
