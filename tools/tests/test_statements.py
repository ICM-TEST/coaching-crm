#!/usr/bin/env python3
"""Bank statements from any bank, CSV or PDF: the lines the head coach's Claude reads into hub/bank/lines/, and the
checks the bank recon makes on them before anything is recorded.

Run from the repo root:  python3 tools/tests/test_statements.py
Every name, number and amount here is invented.
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent / "workspace"
sys.path.insert(0, str(REPO / "scripts"))
from crm.common import money, read_table  # noqa: E402
from recon import balance_break  # noqa: E402

HEADER = ["date", "description", "amount", "balance"]


class Statements(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "work"
        shutil.copytree(REPO / "_templates" / "drive", self.root)
        shutil.rmtree(self.root / "coach-template")
        (self.root / "hub/alex.me.txt").write_text("name: Alex Test\nslug: alex\nrole: head-coach\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def upload(self, statement):
        (self.root / "hub/bank" / statement).write_bytes(b"%PDF-1.4 a made-up statement")

    def read_into_lines(self, statement, rows):
        with (self.root / "hub/bank/lines" / f"{statement}.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)

    def recon(self, *extra):
        p = subprocess.run([sys.executable, "-B", "scripts/recon.py", "--root", str(self.root), "bank", *extra],
                           cwd=REPO, capture_output=True, text=True, env=dict(os.environ, CRM_TODAY="2026-10-30"))
        return p.returncode, p.stdout + p.stderr

    def ledger(self):
        return read_table(self.root / "hub/eft-ledger.csv")

    def test_a_statement_nobody_has_read_stops_the_recon(self):
        self.upload("October.pdf")
        (self.root / ".drive-index.csv").write_text("path,size\nhub/bank/November.csv,900\n")   # listed, not downloaded
        code, out = self.recon()
        self.assertEqual(code, 4, out)
        self.assertIn("haven't been read", out)
        self.assertIn("October.pdf", out)
        self.assertIn("November.csv", out)
        self.assertEqual(self.ledger(), [])

    def test_oldest_first_and_newest_first_both_pass(self):
        self.upload("A.csv")
        self.read_into_lines("A.csv", [["2026-10-01", "ONE", "100.00", "1100.00"],
                                       ["2026-10-02", "FEES", "-10.00", "1090.00"],
                                       ["2026-10-03", "TWO", "200.00", "1290.00"]])
        self.upload("B.pdf")
        self.read_into_lines("B.pdf", [["2026-10-06", "FOUR", "50.00", "1390.00"],          # newest first
                                       ["2026-10-05", "THREE", "50.00", "1340.00"]])
        code, out = self.recon()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.ledger()), 4)                                              # money in only
        self.assertIn("every balance checked", out)
        self.assertIn("A.csv: 3 lines, 2026-10-01 to 2026-10-03, money in 300.00 (2), money out -10.00 (1)", out)

    def test_a_misread_line_stops_the_recon(self):
        self.upload("October.pdf")
        self.read_into_lines("October.pdf", [["2026-10-01", "ONE", "100.00", "1100.00"],
                                             ["2026-10-02", "TWO", "200.00", "1300.00"],
                                             ["2026-10-03", "THREE", "350.00", "1600.00"],  # misread: 300.00
                                             ["2026-10-04", "FOUR", "50.00", "1650.00"]])
        code, out = self.recon()
        self.assertEqual(code, 4, out)
        self.assertIn("lines/October.pdf line 3", out)
        self.assertEqual(self.ledger(), [])                                                  # nothing recorded
        code, out = self.recon("--skip-balance-check")                                       # the head coach's call
        self.assertEqual(code, 0, out)
        self.assertIn("balance check SKIPPED", out)

    def test_a_statement_without_balances_asks_for_a_total_check(self):
        self.upload("Export.csv")
        self.read_into_lines("Export.csv", [["2026-10-01", "ONE", "100.00", ""], ["2026-10-02", "TWO", "250.00", ""]])
        code, out = self.recon()
        self.assertEqual(code, 0, out)
        self.assertIn("money in 350.00 (2)", out)
        self.assertIn("no running balance", out)

    def test_values_must_be_in_the_one_layout(self):
        self.upload("October.pdf")
        self.read_into_lines("October.pdf", [["27/10/2026", "ONE", "100.00", ""], ["2026-10-28", "TWO", "1,400.00", ""]])
        code, out = self.recon()
        self.assertEqual(code, 4, out)
        self.assertIn("date '27/10/2026' isn't YYYY-MM-DD", out)
        self.assertIn("amount '1,400.00' isn't a plain number", out)

    def test_overlapping_statements_count_each_payment_once(self):
        for name, rows in (("Mid-October.csv", [["2026-10-01", "ONE", "100.00", "1100.00"],
                                                ["2026-10-02", "TWO", "200.00", "1300.00"]]),
                           ("October.csv", [["2026-10-01", "ONE", "100.00", "1100.00"],
                                            ["2026-10-02", "TWO", "200.00", "1300.00"],
                                            ["2026-10-03", "THREE", "50.00", "1350.00"]])):
            self.upload(name)
            self.read_into_lines(name, rows)
        code, out = self.recon()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.ledger()), 3)
        self.assertNotIn("Possible double", out)

    def test_the_same_payment_in_a_csv_and_a_pdf_is_flagged(self):
        self.upload("October.csv")
        self.read_into_lines("October.csv", [["2026-10-27", "2026-02-491 NALEDI", "700.00", ""]])
        self.upload("October.pdf")
        self.read_into_lines("October.pdf", [["2026-10-27", "PAYMENT FROM 2026-02-491 NALEDI", "700.00", ""]])
        code, out = self.recon()
        self.assertEqual(code, 0, out)
        self.assertIn("Possible double: October.pdf has 700.00 on 2026-10-27", out)

    def test_money_reads_any_currency(self):
        for text, value in (("$1,440.00", "1440.00"), ("€ 12.50", "12.50"), ("ZAR 1 440.00", "1440.00"),
                            ("(85.00)", "-85.00"), ("-£85", "-85.00"), ("1440", "1440.00")):
            self.assertEqual(money(text), Decimal(value), text)

    def test_balance_break_names_the_line(self):
        rows = [{"amount": a, "balance": b} for a, b in (("0", "100"), ("10", "110"), ("10", "125"))]
        self.assertEqual(balance_break(rows), 3)
        self.assertIsNone(balance_break(rows[:2]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
