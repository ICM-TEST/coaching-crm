#!/usr/bin/env python3
"""The parts that keep Drive use down, on made-up data: one read on a start, and a recon that fetches only the invoice
lists it has to. Needs only Python 3.10+."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from crm.books import audit_coach_folder, lists_needed  # noqa: E402
from crm.common import Drive, coach_me, frontmatter  # noqa: E402


def run(script: str, root: Path, *args: str) -> str:
    p = subprocess.run([sys.executable, "-B", f"scripts/{script}", "--root", str(root), *args], cwd=REPO,
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout


class Usage(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "_templates" / "drive", self.root, dirs_exist_ok=True)
        (self.root / "factory/business.txt").write_text("trading_name: Made Up Coaching\ninvoice_day: 24\n")
        (self.root / "factory/release.txt").write_text("version: 9.9.9\n")
        run("coaches.py", self.root, "add", "--name", "Riley Example", "--phone", "0820000001",
            "--email", "riley@example.com", "--invoice-start", "490")
        self.coach = self.root / "coach-riley"

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_a_coach_starts_on_one_read(self):
        me = frontmatter(coach_me(self.coach))
        self.assertEqual((me["invoice_day"], me["release"], me["coach_number"]), ("24", "9.9.9", "01"))

    def test_the_identity_doc_keeps_its_values_when_factory_isnt_downloaded(self):
        shutil.rmtree(self.root / "factory")                                   # a job that didn't download factory/
        run("build_lists.py", self.root, "coach-clients")
        me = frontmatter(coach_me(self.coach))
        self.assertEqual((me["invoice_day"], me["release"]), ("24", "9.9.9"))

    def test_the_head_coach_starts_on_one_generated_doc(self):
        with (self.root / "hub/clients.csv").open("a") as f:
            f.write("C0001,Sam Sample,0820000002,,active,riley,2026-01-01,\nC0002,Jo Placeholder,0820000003,,new,,2026-01-02,\n")
        (self.root / "factory/client-form.txt").write_text("link: https://forms.example.com/x\n")
        run("build_lists.py", self.root, "coach-clients")
        start = frontmatter(self.root / "hub/start.txt")
        self.assertEqual((start["coaches"], start["clients"], start["unallocated"], start["release"]), ("1", "2", "1", "9.9.9"))
        self.assertEqual(start["client_form_link"], "https://forms.example.com/x")

    def test_start_is_never_made_by_a_job_that_didnt_download_it(self):
        (self.root / "hub/start.txt").unlink()
        run("build_lists.py", self.root, "coach-clients")
        self.assertFalse((self.root / "hub/start.txt").exists())               # or the plan would create a second one

    def test_recon_fetches_only_new_or_changed_lists(self):
        with (self.root / "hub/all-invoices.csv").open("a") as f:
            for lst in ("2026-08", "2026-09"):
                f.write(f"riley,{lst},seal-x,2026-10-01,RE-2026-0001,2026-09-24,C0001,Sam,,2026-01-1,100.00,,,,\n")
        (self.root / ".drive-index.csv").write_text(
            "path,size,modified\n"
            "coach-riley/invoice-lists/2026-08,,2026-08-24\n"                  # copied, untouched since: not fetched
            "coach-riley/invoice-lists/2026-09,,2026-10-03\n"                  # copied, then modified: fetched and checked
            "coach-riley/invoice-lists/2026-10,,2026-10-24\n"                  # new: fetched
            "coach-riley/invoice-lists/README,,2026-01-01\n"
            "coach-riley/pops/x.pdf,100,2026-10-02\n")
        self.assertEqual(lists_needed(Drive(self.root)),
                         ["coach-riley/invoice-lists/2026-09", "coach-riley/invoice-lists/2026-10"])
        out = run("recon.py", self.root, "lists-needed")
        self.assertIn("coach-riley/invoice-lists/2026-10", out)
        self.assertNotIn("2026-08", out)

    def test_a_listing_without_dates_fetches_everything(self):
        with (self.root / "hub/all-invoices.csv").open("a") as f:
            f.write("riley,2026-08,seal-x,2026-10-01,RE-2026-0001,2026-09-24,C0001,Sam,,2026-01-1,100.00,,,,\n")
        (self.root / ".drive-index.csv").write_text("path,size\ncoach-riley/invoice-lists/2026-08,\n")
        self.assertEqual(lists_needed(Drive(self.root)), ["coach-riley/invoice-lists/2026-08"])

    def test_a_pdf_the_coach_kept_off_the_drive_isnt_a_problem(self):
        lists = [({"file": "2026-10", "problem": ""}, [{"pdf": "invoices/2026-10/Invoice 2026-01-490.pdf", "pdf_sha": "x"}])]
        self.assertEqual(audit_coach_folder(self.coach, lists, {}), [])


if __name__ == "__main__":
    unittest.main()
