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

REPO = Path(__file__).resolve().parent.parent.parent


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
        (self.work / "hub/morgan.me.txt").write_text("name: Morgan Head\nslug: morgan\nrole: head-coach\n")
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

    def test_coach_issues_invoices(self):
        run("sync.py", "snapshot", str(self.work))
        drafts = self.tmp / "drafts.json"
        drafts.write_text(json.dumps({"invoices": [{"client_id": "C0001", "lines": [{"code": "PVT", "month": "2026-10",
                                                                                     "qty": 2}]}]}))
        run("issue.py", "--root", str(self.work), "--coach-dir", "coach-riley", "--period", "2026-10",
            "--drafts", str(drafts))
        ops = self.ops("--role", "coach", "--coach", "coach-riley")
        self.assertEqual([(o["op"], o["path"]) for o in ops],
                         [("hand_over", "coach-riley/invoices/2026-10/Invoice 2026-01-490.pdf"),   # to the coach, in the chat
                          ("create_sheet", "coach-riley/invoice-lists/2026-10"),          # the only thing written to the drive
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
        (self.work / "coach-riley/invoices/extra").mkdir(parents=True)                    # not a month folder
        (self.work / "coach-riley/invoices/extra/x.pdf").write_bytes(b"%PDF")
        c = self.work / "coach-riley/clients.csv"
        c.write_text(c.read_text() + "C0099,Someone,,,active,2026-10-01\n")               # a generated Sheet
        (self.work / "coach-riley/invoice-lists/README.txt").unlink()                     # a deletion
        out = self.plan("--role", "coach", "--coach", "coach-riley", ok=(1,))
        for expected in ("coach-riley/invoices/extra: a coach's Claude writes only its invoice-list Sheets",
                         "coach-riley/invoices/extra/x.pdf: a coach's Claude writes only its invoice-list Sheets",
                         "coach-riley/clients: a coach's Claude writes only",
                         "coach-riley/invoice-lists/README.txt: deleted"):
            self.assertIn(expected, out)
        self.assertIn("don't write anything to the drive", out)

    def test_head_coach_recon_writes(self):
        drafts = self.tmp / "drafts.json"
        drafts.write_text(json.dumps({"invoices": [{"client_id": "C0001", "lines": [{"code": "PVT", "month": "2026-10",
                                                                                     "qty": 2}]}]}))
        run("issue.py", "--root", str(self.work), "--coach-dir", "coach-riley", "--period", "2026-10",
            "--drafts", str(drafts))
        run("sync.py", "snapshot", str(self.work))
        index = self.work / ".drive-index.csv"                                             # the statement: listed, not downloaded
        index.write_text((index.read_text() if index.exists() else "path,size\n") + "hub/bank/2026-10-28.pdf,5120\n")
        with (self.work / "hub/bank/lines/2026-10-28.pdf.csv").open("w", newline="") as f:   # what Claude read from it
            w = csv.writer(f)
            w.writerow(["date", "description", "amount", "balance"])
            w.writerow(["2026-10-27", "2026-01-490 ANN", "700.00", "10700.00"])
        run("recon.py", "--root", str(self.work), "bank", "--month-end", "2026-10")
        ops = self.ops("--role", "head-coach")
        self.assertIn(("create_sheet", "hub/bank/lines/2026-10-28.pdf"), [(o["op"], o["path"]) for o in ops])
        proposal = next(o for o in ops if o["op"] == "create_sheet" and o["path"].startswith("hub/recon/bank-"))
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


    # --- the lock, from the audit of 2026-11-10: every one of these must be refused ---

    def refused(self, role, *paths):
        out = self.plan(*role, ok=(1,))
        for path in paths:
            self.assertIn(path + ":", out)

    def test_head_coach_cannot_rewrite_the_money_records(self):
        for name in ("allocations", "eft-ledger", "eft-reviews", "all-invoices", "client-history"):
            f = self.work / f"hub/{name}.csv"
            f.write_text(f.read_text() + "x,y\n")
        run("sync.py", "snapshot", str(self.work))
        for name in ("allocations", "eft-ledger", "eft-reviews", "all-invoices", "client-history"):
            f = self.work / f"hub/{name}.csv"
            f.write_text(f.read_text().replace("x,y\n", "changed,y\n"))
        self.refused(("--role", "head-coach"), "hub/allocations", "hub/eft-ledger", "hub/eft-reviews", "hub/all-invoices",
                     "hub/client-history")

    def test_head_coach_may_still_add_to_them(self):
        run("sync.py", "snapshot", str(self.work))
        f = self.work / "hub/client-history.csv"
        f.write_text(f.read_text() + "2026-11-01,C0001,coach riley,moved\n")
        self.assertEqual([o["op"] for o in self.ops("--role", "head-coach")], ["append"])

    def test_head_coach_cannot_invent_a_top_level_folder(self):
        run("sync.py", "snapshot", str(self.work))
        (self.work / "movies").mkdir()
        (self.work / "movies/list.txt").write_text("x")
        self.refused(("--role", "head-coach"), "movies", "movies/list")

    def test_head_coach_cannot_hide_a_file_in_a_coach_folder_by_its_name(self):
        run("sync.py", "snapshot", str(self.work))
        (self.work / "coach-riley/invoice-lists/clients.csv").write_text("period:,2026-10\n")
        (self.work / "coach-riley/pops/unpaid.csv").write_text("x\n")
        self.refused(("--role", "head-coach"), "coach-riley/invoice-lists/clients", "coach-riley/pops/unpaid")

    def test_a_coach_can_only_create_real_invoice_lists(self):
        run("sync.py", "snapshot", str(self.work))
        (self.work / "coach-riley/invoice-lists/shopping.csv").write_text("milk\n")
        (self.work / "coach-riley/invoice-lists/2026-10.csv").write_text("milk\n")          # right name, not a list
        self.refused(("--role", "coach", "--coach", "coach-riley"), "coach-riley/invoice-lists/shopping",
                     "coach-riley/invoice-lists/2026-10")


if __name__ == "__main__":
    unittest.main(verbosity=2)
