#!/usr/bin/env python3
"""The invoice generator on made-up data: numbering, the two outputs, and every refusal.

Run from the repo root:  python3 tools/tests/test_issue.py      (needs reportlab)
"""
import base64
import json
import os
import re
import zlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent / "workspace"
sys.path.insert(0, str(REPO / "scripts"))
from crm.books import audit_coach_folder, invoice_lists  # noqa: E402
from crm.common import frontmatter, read_sheet, read_table  # noqa: E402

BUSINESS = """---
trading_name: Example Coaching Co
website: www.example-coaching.test
account_holder: EXCO
bank: Example Bank
branch_code: "000001"
account_type: Business Account
account_number: "1234567890"
currency_symbol: R
payment_instruction: "Please pay the above amount by bank transfer, using {reference} as your reference:"
pop_request: "Please send your coach the POP once paid."
thanks: "Thank you."
sign_off: The Example Coaching Team
invoice_number_format: "{year}-{coach}-{seq}"
invoice_day: 24
payment_terms: due on receipt
---
"""


def pdf_text(path: Path) -> bytes:
    """Everything a PDF draws, with its compressed streams opened up, for checking what's on the page."""
    raw = path.read_bytes()
    out = [raw]
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        data = m.group(1).strip()
        try:
            if data.endswith(b"~>"):                                     # page content: ASCII85, then Flate
                data = base64.a85decode(data[:-2])
            out.append(zlib.decompressobj().decompress(data))
        except (zlib.error, ValueError):
            pass
    return b"".join(out)


class Issue(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "drive"
        shutil.copytree(REPO / "_templates" / "drive", self.root)
        (self.root / "coach-template").rename(self.root / "coach-riley")
        (self.root / "factory/business.txt").write_text(BUSINESS)
        bw = self.root / "factory/billable-work.csv"
        bw.write_text(bw.read_text() + "SQD60,Group Session,per session,240,in advance\n"
                                       "PVT,Private lesson,per lesson,350,after\n")
        (self.root / "coach-riley/riley.me.txt").write_text("---\nname: Riley\nslug: riley\ncode: RY\nrole: coach\n"
                                                      "phone: \"+27820000001\"\nemail: riley@example.test\n"
                                                      "coach_number: 7\ninvoice_start: 490\n---\n")
        (self.root / "coach-riley/clients.csv").write_text(
            "# My clients\n\n## Clients\nid,name,phone,email,status,since\n"
            "C0001,Ann Example,+27820000002,,active,2026-10-01\n"
            "C0002,Bo Example,+27820000003,,active,2026-10-01\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def issue(self, drafts, *extra, ok=(0,)):
        path = self.tmp / "drafts.json"
        path.write_text(json.dumps(drafts))
        p = subprocess.run([sys.executable, "scripts/issue.py", "--root", str(self.root), "--coach-dir", "coach-riley",
                            "--period", "2026-10", "--drafts", str(path), *extra],
                           cwd=REPO, capture_output=True, text=True)
        if p.returncode not in ok:
            raise AssertionError(f"exit {p.returncode}\n{p.stdout}\n{p.stderr}")
        return p.stdout

    DRAFTS = {"invoices": [
        {"client_id": "C0001", "lines": [{"code": "SQD60", "month": "2026-11", "qty": 4},       # group: next month
                                         {"code": "SQD60", "month": "2026-10", "qty": 2}]},     # group: this month
        {"client_id": "C0002", "payer": "Cy Parent", "lines": [{"code": "PVT", "month": "2026-10", "qty": 3}]}]}

    def test_two_outputs_and_numbering(self):
        out = self.issue(self.DRAFTS, "--dry-run")
        self.assertIn("2026-07-490", out)
        self.assertIn("R1,440.00", out)
        self.assertFalse((self.root / "coach-riley/invoice-lists/2026-10.csv").exists(), "a dry run writes nothing")

        issued_output = self.issue(self.DRAFTS)
        lst = self.root / "coach-riley/invoice-lists/2026-10.csv"
        self.assertEqual(read_sheet(lst)[0]["issued"], "2026-10-24")                     # invoice_day
        rows = read_table(lst)
        self.assertEqual([(r["number"], r["reference"], r["amount"], r["payer"]) for r in rows],
                         [("RY-2026-0490", "2026-07-490", "1440.00", ""),
                          ("RY-2026-0491", "2026-07-491", "1050.00", "Cy Parent")])
        for r in rows:
            pdf = self.root / "coach-riley" / r["pdf"]
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"), r["pdf"])
        first_pdf = self.root / "coach-riley" / rows[0]["pdf"]
        self.assertLess(first_pdf.stat().st_size, 60_000, "invoices stay small: they pile up every month")
        first = pdf_text(first_pdf)
        for printed in (b"using 2026-07-490 as your reference", b"+27820000001", b"riley@example.test",   # coach
                        b"Ann Example", b"+27820000002",                                                # client
                        b"Group Session - November", b"R1,440.00", b"2026-07-490"):
            self.assertIn(printed, first)
        for weight in (b"Inter-Regular", b"Inter-Medium", b"Inter-SemiBold", b"Inter-Bold"):
            self.assertIn(weight, first)                                                # the business's own font
        files = sorted(p.name for p in (self.root / "coach-riley").rglob("*") if p.is_file() and p.name != "README.txt")
        self.assertEqual(files, sorted(["riley.me.txt", "clients.csv", "unpaid.csv", ".keep", "2026-10.csv",
                                        "Invoice 2026-07-490.pdf", "Invoice 2026-07-491.pdf"]), "only the two outputs are added")

        lists = invoice_lists(self.root / "coach-riley")
        self.assertEqual([m["problem"] for m, _ in lists], [""])                       # sealed by the generator
        self.assertEqual(audit_coach_folder(self.root / "coach-riley", lists, {}), [])      # nothing out of place
        # connector mode: what to download first, and what to upload after, PDFs before the list
        needs = subprocess.run([sys.executable, "scripts/issue.py", "--coach-dir", "coach-riley", "--needs"], cwd=REPO,
                               capture_output=True, text=True, check=True).stdout
        for path in ("coach-riley/riley.me", "coach-riley/clients", "coach-riley/invoice-lists/*",
                     "factory/business", "factory/billable-work", "factory/invoice-template/fonts/*.ttf"):
            self.assertIn(path, needs)
        up = issued_output.split("Upload, in this order")[1]
        self.assertLess(up.index("Invoice 2026-07-491.pdf"), up.index("coach-riley/invoice-lists/2026-10"))
        self.assertIn("— LAST", up)
        out = self.issue(self.DRAFTS, ok=(1,))
        self.assertIn("already issued", out)                                            # one run, one list

    def test_makes_its_own_month_folder(self):
        month = self.root / "coach-riley/invoices/2026-10"
        self.assertFalse(month.exists())                                 # nobody opens a month first
        self.issue(self.DRAFTS, "--dry-run")
        self.assertFalse(month.exists(), "a dry run makes nothing")
        self.issue(self.DRAFTS)
        self.assertTrue(list(month.glob("*.pdf")))

    def test_refusals(self):
        bad = {"invoices": [
            {"client_id": "C0009", "lines": [{"code": "PVT", "month": "2026-10", "qty": 1}]},          # not my client
            {"client_id": "C0001", "lines": [{"code": "XYZ", "month": "2026-10", "qty": 1}]},          # not a rate
            {"client_id": "C0002", "lines": [{"code": "PVT", "month": "2026-11", "qty": 1},            # private: not given yet
                                             {"code": "SQD60", "month": "2026-12", "qty": 1}]},        # group: too far ahead
            {"client_id": "C0002", "lines": [{"code": "PVT", "month": "2026-10", "qty": 0}]}]}         # twice, and qty 0
        out = self.issue(bad, ok=(1,))
        for expected in ("C0009 isn't on your client list", "'XYZ' isn't in factory/billable-work",
                         "not after 2026-10 (Private lesson is billed for the month past)",
                         "not after 2026-11 (Group Session is billed in advance", "two invoices in this run", "quantity must be above zero"):
            self.assertIn(expected, out)
        self.assertFalse(list((self.root / "coach-riley/invoice-lists").glob("2026-*.csv")), "nothing issued")
        out = self.issue({"updates": [{"invoice": "RY-2026-0999", "lines": [{"code": "PVT", "month": "2026-10", "qty": 1}]}]}, ok=(1,))
        self.assertIn("isn't one of your issued invoices", out)
        out = self.issue({"credit_notes": [{"applies_to": "RY-2026-0999", "amount": "10"}]}, ok=(1,))
        self.assertIn("no credit notes", out)

    def test_every_coach_needs_a_coach_number(self):
        me = self.root / "coach-riley/riley.me.txt"
        me.write_text(me.read_text().replace("coach_number: 7\n", ""))
        self.assertIn("has no coach_number", self.issue(self.DRAFTS, ok=(1,)))

    def test_an_unfinished_business_doc_issues_nothing(self):
        shutil.copy(REPO / "_templates/drive/factory/business.txt", self.root / "factory/business.txt")
        out = self.issue(self.DRAFTS, "--dry-run", ok=(1,))
        self.assertIn("isn't finished", out)                     # the template's <placeholders> are still there
        self.assertIn("invoice_day", out)

    def test_amounts_are_in_rand_unless_the_business_says_otherwise(self):
        biz = self.root / "factory/business.txt"
        biz.write_text(biz.read_text().replace("currency_symbol: R\n", ""))
        self.assertIn("R1,440.00", self.issue(self.DRAFTS, "--dry-run"))

    def test_nothing_to_bill_still_marks_the_run_done(self):
        self.issue({"invoices": []})
        self.assertEqual(read_table(self.root / "coach-riley/invoice-lists/2026-10.csv"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
