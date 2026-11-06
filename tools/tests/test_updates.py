#!/usr/bin/env python3
"""Updating an unpaid invoice, through to the bank recon, on made-up data.

The rule: a client cancels before paying, so the coach re-issues the invoice with the new amount. It keeps its number
and the recon uses the new amount. Once it's paid it stays as it is, and the coach adjusts their future invoices.

Run from the repo root:  python3 tools/tests/test_updates.py      (needs reportlab)
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
sys.path.insert(0, str(REPO / "scripts"))
from crm.books import invoice_lists  # noqa: E402
from crm.common import read_sections, read_table  # noqa: E402

PVT2 = [{"code": "PVT", "month": "2026-10", "qty": 2}]           # R700
GROUP = {"code": "SQD", "month": "2026-11", "qty": 4}            # R720, billed in advance


class Updates(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.w = self.tmp / "work"
        shutil.copytree(REPO / "_templates/drive", self.w)
        shutil.rmtree(self.w / "coach-template")
        (self.w / "factory/business.txt").write_text("trading_name: Example Coaching Co\nbank: Example Bank\n"
                                                     "invoice_number_format: {year}-{coach}-{seq}\ninvoice_day: 24\n")
        bw = self.w / "factory/billable-work.csv"
        bw.write_text(bw.read_text() + "PVT,Private lesson,per lesson,350,after\nSQD,Group session,per session,180,in advance\n")
        (self.w / "hub/me.txt").write_text("name: Morgan Head\nslug: morgan\nrole: head-coach\n")
        self.run_ok("coaches.py", "add", "--name", "Riley Coach", "--phone", "0820000002", "--email", "q@example.test",
                    "--invoice-start", "490")
        c = self.w / "hub/clients.csv"
        c.write_text(c.read_text() + "C0001,Sipho Example,0830000001,,active,riley,2026-10-01,\n"
                                     "C0002,Naledi Example,0830000002,,active,riley,2026-10-01,\n")
        self.run_ok("build_lists.py", "coach-clients")
        self.run_ok("runs.py", "open", "2026-10")
        self.issue({"invoices": [{"client_id": "C0001", "lines": PVT2 + [{"code": "PVT", "month": "2026-10", "qty": 2}, GROUP]},
                                 {"client_id": "C0002", "lines": PVT2}]})       # 2026-01-490 R2120, 2026-01-491 R700
        self.bank_n = 0

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_(self, script, *a):
        return subprocess.run([sys.executable, "-B", f"scripts/{script}", "--root", str(self.w), *a], cwd=REPO,
                              capture_output=True, text=True)

    def run_ok(self, script, *a):
        p = self.run_(script, *a)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def issue(self, drafts, *extra, ok=True):
        path = self.tmp / "drafts.json"
        path.write_text(json.dumps(drafts))
        p = self.run_("issue.py", "--coach-dir", "coach-riley", "--period", "2026-10", "--drafts", str(path), *extra)
        self.assertEqual(p.returncode, 0 if ok else 1, p.stdout + p.stderr)
        return p.stdout

    def update_to_1400(self, ok=True):
        return self.issue({"updates": [{"invoice": "2026-01-490", "lines": [{"code": "PVT", "month": "2026-10", "qty": 4}]}]}, ok=ok)

    def recon(self, *lines):
        self.bank_n += 1
        with (self.w / f"hub/bank/b{self.bank_n}.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Description", "Amount", "Balance"])
            w.writerows([["2026/10/27", d, a, "10000.00"] for d, a in lines])
        before = set((self.w / "hub/recon").glob("bank-*.csv"))
        self.run_ok("recon.py", "bank", "--month-end", "2026-10")
        new = (set((self.w / "hub/recon").glob("bank-*.csv")) - before).pop()
        self.run_ok("recon.py", "push", str(new))

    def unpaid(self):
        return {r["invoice"]: r for r in read_sections(self.w / "coach-riley/unpaid.csv")["Unpaid invoices"]}

    def summary(self):
        return read_sections(self.w / "hub/summary.csv")

    def test_update_then_pays_the_new_amount(self):
        out = self.update_to_1400()
        self.assertIn("was R2,120.00", out)
        self.assertTrue((self.w / "coach-riley/invoices/2026-10/Invoice 2026-01-490 (updated).pdf").exists())
        self.assertTrue((self.w / "coach-riley/invoices/2026-10/Invoice 2026-01-490.pdf").exists(), "the original stays")
        rows = read_table(self.w / "coach-riley/invoice-lists/2026-10-2.csv")
        self.assertEqual((rows[0]["reference"], rows[0]["amount"], rows[0]["date"]), ("2026-01-490", "1400.00", "2026-10-24"))
        self.recon(("2026-01-490 SIPHO", "1400.00"))
        self.assertNotIn("2026-01-490", self.unpaid())
        s = self.summary()
        by = s["By coach"][0]
        self.assertEqual((by["invoices"], by["invoiced"], by["collected"], by["outstanding"]), ("2", "2100.00", "1400.00", "700.00"))
        up = s["Updated invoices — re-issued by the coach with a new amount"][0]
        self.assertEqual((up["invoice"], up["was"], up["now"]), ("2026-01-490", "2120.00", "1400.00"))
        self.assertEqual(s["Folder checks — things the system didn't make, or that changed"], [])
        arch = [r for r in read_table(self.w / "hub/all-invoices.csv") if r["reference"] == "2026-01-490"]
        self.assertEqual([r["amount"] for r in arch], ["2120.00", "1400.00"])            # Morgan's copy keeps both

    def test_new_amount_survives_later_recons(self):
        self.update_to_1400()
        self.recon(("2026-01-491 NALEDI", "700.00"))                                     # both lists now copied
        self.assertEqual(self.unpaid()["2026-01-490"]["still_owed"], "1400.00")
        self.recon(("2026-01-490 SIPHO", "1400.00"))
        self.assertNotIn("2026-01-490", self.unpaid())

    def test_recon_ran_before_the_update(self):
        self.recon(("2026-01-490 SIPHO", "1400.00"))                                     # paid the lower amount first
        self.assertEqual(self.unpaid()["2026-01-490"]["still_owed"], "720.00")
        self.update_to_1400()
        self.recon()
        self.assertNotIn("2026-01-490", self.unpaid())

    def test_paid_in_full_is_refused(self):
        self.recon(("2026-01-490 SIPHO", "2120.00"))
        self.assertIn("already paid", self.update_to_1400(ok=False))
        self.assertFalse((self.w / "coach-riley/invoice-lists/2026-10-2.csv").exists())

    def test_cant_go_below_what_is_paid(self):
        self.recon(("2026-01-490 SIPHO", "1500.00"))
        self.assertIn("can't go down to", self.update_to_1400(ok=False))

    def test_paid_in_the_bank_but_no_recon_yet(self):
        self.update_to_1400()
        self.recon(("2026-01-490 SIPHO", "2120.00"))                                     # the coach couldn't have known
        self.assertNotIn("2026-01-490", self.unpaid())
        over = self.summary()["Overpayments — handle in your own accounting system"]
        self.assertEqual(over[0]["amount"], "720.00")                                    # Morgan is told

    def test_two_updates_latest_wins(self):
        self.update_to_1400()
        self.issue({"updates": [{"invoice": "2026-01-490", "lines": PVT2}]})
        self.assertTrue((self.w / "coach-riley/invoices/2026-10/Invoice 2026-01-490 (updated 2).pdf").exists())
        self.recon(("2026-01-490 SIPHO", "700.00"))
        self.assertNotIn("2026-01-490", self.unpaid())
        self.assertEqual(len(self.summary()["Updated invoices — re-issued by the coach with a new amount"]), 2)

    def test_whole_invoice_cancelled(self):
        self.assertIn("no billable lines", self.issue({"updates": [{"invoice": "2026-01-490", "lines": []}]}, ok=False))
        self.issue({"updates": [{"invoice": "2026-01-490", "cancel": True, "lines": []}]})
        self.recon()
        self.assertNotIn("2026-01-490", self.unpaid())
        self.assertIn("2026-01-491", self.unpaid())

    def test_a_hand_changed_update_is_left_out(self):
        self.update_to_1400()
        path = self.w / "coach-riley/invoice-lists/2026-10-2.csv"
        path.write_text(path.read_text().replace("1400.00", "100.00"))
        self.recon()
        self.assertEqual(self.unpaid()["2026-01-490"]["still_owed"], "2120.00")          # the sealed amount stands
        self.assertTrue(any("was changed after it was issued" in r["problem"]
                            for r in self.summary()["Folder checks — things the system didn't make, or that changed"]))

    def test_update_order_and_run_count(self):
        self.update_to_1400()
        files = [m["file"] for m, _ in invoice_lists(self.w / "coach-riley")]
        self.assertEqual(files, ["2026-10", "2026-10-2"])
        status = self.run_ok("runs.py", "status", "2026-10")
        self.assertIn("2100.00", status)                                                 # not counted twice

    def test_drive_plan_allows_it(self):
        subprocess.run([sys.executable, "-B", "scripts/sync.py", "snapshot", str(self.w)], cwd=REPO, check=True, capture_output=True)
        self.update_to_1400()
        p = subprocess.run([sys.executable, "-B", "scripts/sync.py", "plan", str(self.w), "--role", "coach", "--coach", "coach-riley",
                            "--json"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual([o["op"] for o in json.loads(p.stdout)], ["upload", "create_sheet", "lock", "lock"])

    def test_needs_the_unpaid_list(self):
        (self.w / "coach-riley/unpaid.csv").unlink()
        self.assertIn("Download it first", self.update_to_1400(ok=False))

    def test_wrong_period_and_nothing_to_change(self):
        path = self.tmp / "d.json"
        path.write_text(json.dumps({"updates": [{"invoice": "2026-01-490", "lines": PVT2}]}))
        self.run_ok("runs.py", "open", "2026-11")
        p = self.run_("issue.py", "--coach-dir", "coach-riley", "--period", "2026-11", "--drafts", str(path))
        self.assertIn("Use --period 2026-10", p.stdout)
        self.assertIn("nothing to update", self.issue({"updates": [{"invoice": "2026-01-491", "lines": PVT2}]}, ok=False))


if __name__ == "__main__":
    unittest.main(verbosity=1)
