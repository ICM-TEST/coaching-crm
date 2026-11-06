#!/usr/bin/env python3
"""sync.py on made-up data: each job's changes become the right connector steps, in order, within the role's limits.

Run from the repo root:  python3 tools/tests/test_sync.py      (needs reportlab, for the invoice step)
"""
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent / "workspace"


def run(script, *args, ok=(0,)):
    p = subprocess.run([sys.executable, f"scripts/{script}", *args], cwd=REPO, capture_output=True, text=True)
    if p.returncode not in ok:
        raise AssertionError(f"{script} {args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p.stdout


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.work = self.tmp / "work"                      # a working copy, as downloaded through the connectors
        shutil.copytree(REPO / "_templates" / "drive", self.work)
        shutil.rmtree(self.work / "coach-template")
        (self.work / "factory/business.txt").write_text(
            "trading_name: Example Coaching Co\nbank: Example Bank\ninvoice_number_format: {year}-{coach}-{seq}\n"
            "invoice_day: 24\n")
        bw = self.work / "factory/billable-work.csv"
        bw.write_text(bw.read_text() + "PVT,Private lesson,per lesson,350,after\n")
        (self.work / "hub/me.txt").write_text("name: Morgan Head\nslug: morgan\nrole: head-coach\n")
        run("coaches.py", "--root", str(self.work), "add", "--name", "Riley Coach", "--phone", "+27820000002",
            "--email", "q@example.test", "--invoice-start", "490")
        clients = self.work / "hub/clients.csv"
        clients.write_text(clients.read_text() + "C0001,Ann Example,+27820000009,,active,riley,2026-10-01,\n")
        run("build_lists.py", "--root", str(self.work), "coach-clients")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def plan(self, *role, ok=(0,)):
        return run("sync.py", "plan", str(self.work), *role, ok=ok)

    def ops(self, *role):
        return json.loads(self.plan(*role, "--json"))

    def test_head_coach_opens_a_run(self):
        run("sync.py", "snapshot", str(self.work))
        run("runs.py", "--root", str(self.work), "open", "2026-10")
        ops = self.ops("--role", "head-coach")
        self.assertEqual([(o["op"], o["path"]) for o in ops],
                         [("create_folder", "coach-riley/invoices/2026-10"),
                          ("append", "factory/invoicing-runs")])
        self.assertEqual(ops[1]["values"][0][0], "'2026-10")

    def test_coach_issues_invoices(self):
        run("runs.py", "--root", str(self.work), "open", "2026-10")
        run("sync.py", "snapshot", str(self.work))
        drafts = self.tmp / "drafts.json"
        drafts.write_text(json.dumps({"invoices": [{"client_id": "C0001", "lines": [{"code": "PVT", "month": "2026-10",
                                                                                     "qty": 2}]}]}))
        run("issue.py", "--root", str(self.work), "--coach-dir", "coach-riley", "--period", "2026-10",
            "--drafts", str(drafts))
        ops = self.ops("--role", "coach", "--coach", "coach-riley")
        self.assertEqual([(o["op"], o["path"]) for o in ops],
                         [("upload", "coach-riley/invoices/2026-10/Invoice 2026-01-490.pdf"),
                          ("create_sheet", "coach-riley/invoice-lists/2026-10"),          # the list after its PDF
                          ("lock", "coach-riley/invoices/2026-10/Invoice 2026-01-490.pdf"),
                          ("lock", "coach-riley/invoice-lists/2026-10")])
        sheet = ops[1]["values"]
        self.assertIn(["'made_by:", "'issue.py"], sheet)                                  # the seal block travels
        self.assertTrue(any(r[:1] == ["'seal:"] and r[1].startswith("'seal-") for r in sheet))
        self.assertIn("Carry these out in this order", self.plan("--role", "coach", "--coach", "coach-riley"))

    def test_every_sheet_value_is_written_as_plain_text(self):
        """A real Sheet turns 0820000003 into 820000003 and 2026-01-5 into a date unless each cell is protected."""
        run("sync.py", "snapshot", str(self.work))
        clients = self.work / "hub/clients.csv"
        clients.write_text(clients.read_text() + "C0002,=SUM(1;2),0820000003,'t Hooft,active,riley,2026-10-01,\n")
        ops = self.ops("--role", "head-coach")
        row = next(o for o in ops if o["path"] == "hub/clients")["values"][-1]
        self.assertEqual(row, ["'C0002", "'=SUM(1;2)", "'0820000003", "''t Hooft", "'active", "'riley", "'2026-10-01", ""])
        for op in ops:
            for r in op.get("values", []):
                self.assertTrue(all(c == "" or c.startswith("'") for c in r), f"{op['path']}: {r}")

    def test_a_coach_may_not_do_anything_else(self):
        run("sync.py", "snapshot", str(self.work))
        (self.work / "coach-riley/invoices/2026-11").mkdir(parents=True)                  # a folder: Morgan's job
        (self.work / "coach-riley/invoices/2026-11/x.pdf").write_bytes(b"%PDF")
        c = self.work / "coach-riley/clients.csv"
        c.write_text(c.read_text() + "C0099,Someone,,,active,2026-10-01\n")               # a generated Sheet
        (self.work / "coach-riley/invoice-lists/README.txt").unlink()                     # a deletion
        out = self.plan("--role", "coach", "--coach", "coach-riley", ok=(1,))
        for expected in ("coach-riley/invoices/2026-11: a coach's Claude may only upload",
                         "coach-riley/invoices/2026-11/x.pdf: a coach's Claude may only upload its PDFs into an existing",
                         "coach-riley/clients: a coach's Claude may only",
                         "coach-riley/invoice-lists/README.txt: deleted"):
            self.assertIn(expected, out)
        self.assertIn("don't write anything to the drive", out)

    def test_head_coach_recon_writes(self):
        run("runs.py", "--root", str(self.work), "open", "2026-10")
        drafts = self.tmp / "drafts.json"
        drafts.write_text(json.dumps({"invoices": [{"client_id": "C0001", "lines": [{"code": "PVT", "month": "2026-10",
                                                                                     "qty": 2}]}]}))
        run("issue.py", "--root", str(self.work), "--coach-dir", "coach-riley", "--period", "2026-10",
            "--drafts", str(drafts))
        with (self.work / "hub/bank/2026-10-28.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Description", "Amount", "Balance"])
            w.writerow(["2026/10/27", "2026-01-490 ANN", "700.00", "10700.00"])
        run("sync.py", "snapshot", str(self.work))
        run("recon.py", "--root", str(self.work), "bank", "--month-end", "2026-10")
        ops = self.ops("--role", "head-coach")
        proposal = next(o for o in ops if o["op"] == "create_sheet")
        self.assertTrue(proposal["path"].startswith("hub/recon/bank-"))
        self.assertEqual(proposal["dropdown"]["column"], "decision")                        # Morgan picks from a list
        self.assertIn(("append", "hub/eft-ledger"), [(o["op"], o["path"]) for o in ops])

        run("sync.py", "snapshot", str(self.work))
        run("recon.py", "--root", str(self.work), "push", str(self.work / (proposal["path"] + ".csv")))
        ops = self.ops("--role", "head-coach")
        kinds = {(o["op"], o["path"]) for o in ops}
        for expected in (("append", "hub/allocations"), ("append", "hub/all-invoices"),     # Morgan's copy
                         ("rewrite", "coach-riley/unpaid"), ("rewrite", "hub/summary"),
                         ("rewrite", proposal["path"])):                                     # marked pushed
            self.assertIn(expected, kinds)
        self.assertFalse([o for o in ops if o["path"].startswith("coach-riley/invoice")], "Morgan never writes a coach's invoices")


if __name__ == "__main__":
    unittest.main(verbosity=2)
