#!/usr/bin/env python3
"""A full cycle on made-up data: 8 coaches, the invoicing-run gate, both recons (bank and
proof of payment), the unreconciled live list, overpayments and write-offs.

Run from the repo root:  python3 tools/tests/test_cycle.py      (KEEP=1 keeps the test drive)
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
from crm.books import GENERATOR, file_hash, list_seal  # noqa: E402
from crm.common import append_rows, read_sheet, read_table, rewrite_table, write_sheet  # noqa: E402

COACHES = [("morgan", "CH", "Morgan"), ("ayanda", "AY", "Ayanda"), ("ben", "BN", "Ben"), ("dineo", "DN", "Dineo"),
           ("ethan", "ET", "Ethan"), ("fatima", "FT", "Fatima"), ("gareth", "GR", "Gareth"), ("hannah", "HN", "Hannah")]
# coach -> [(client_id, name, payer, invoice amount)]
CLIENTS = {
    "ayanda": [("C0001", "Sipho Ndlovu", "", 1400), ("C0002", "Naledi Khumalo", "", 1400), ("C0003", "Thandi Radebe", "", 720)],
    "ben": [("C0004", "Kagiso Pule", "", 1050), ("C0005", "Andile Sithole", "", 350), ("C0006", "Lerato Mokoena", "", 700)],
    "hannah": [("C0007", "Musa Mokoena", "", 560), ("C0008", "Zanele Dube", "", 900), ("C0009", "Peter Venter", "", 1050)],
    "ethan": [("C0010", "Zola Mthembu", "", 700), ("C0011", "Ayesha Patel", "Rashid Khan", 1050), ("C0012", "Ruan Botha", "", 350)],
    "gareth": [("C0013", "Jabu Nkosi", "", 700), ("C0014", "Lisa Smith", "", 1400), ("C0015", "Tom Smith", "", 1050)],
    "fatima": [("C0016", "Samson Tau", "", 1400), ("C0017", "Nomsa Zulu", "", 720), ("C0018", "Kai Brown", "", 350)],
    "dineo": [("C0019", "Lindiwe Mabaso", "", 1050), ("C0020", "Bongani Shabalala", "", 900), ("C0021", "Grace Nel", "", 350)],
    "morgan": [("C0022", "Mike Olivier", "", 700), ("C0023", "Sarah Jacobs", "", 1400), ("C0024", "Ivan Petrov", "", 1050)],
}
LIST_COLS = ["number", "date", "client_id", "client", "payer", "reference", "amount", "applies_to", "pdf", "pdf_sha",
             "pdf_bytes"]

BANK_1 = [  # date, description, amount
    ("2026/12/02", "AY-0001 SIPHO", "1400.00"),          # reference
    ("2026/12/02", "NALEDI K", "1400.00"),               # client name + amount
    ("2026/12/03", "MOKOENA", "1260.00"),                # one parent, two coaches (BN-0003 700 + HN-0001 560)
    ("2026/12/03", "COACHING", "700.00"),                  # several R700 invoices -> ?
    ("2026/12/03", "SAMSON T", "1500.00"),               # overpaid by 100 -> invoice paid, R100 listed for Morgan
    ("2026/12/04", "TRANSFER FROM SAVINGS", "5000.00"),  # ? -> head coach: non-client
    ("2026/12/04", "SMITH", "1050.00"),                  # two Smiths, one fits the amount
    ("2026/12/04", "ZANELE DUBE", "400.00"),             # part-payment -> ?
    ("2026/12/04", "KP BN 0001", "1050.00"),             # reference with spaces
    ("2026/12/04", "R KHAN", "1050.00"),                 # the payer (a parent), not the client
    ("2026/12/04", "BANK FEES", "-200.00"),              # money out: ignored
    ("2026/12/05", "CH-0002", "1400.00"),                # head coach's own invoice
    ("2026/12/05", "RUAN B", "350.00"),
    ("2026/12/05", "PV HN 3", "1050.00"),                # Peter's, wrong reference -> ? -> unreconciled, later a POP
    ("2026/12/05", "PREPAY JANE", "500.00"),             # no invoice yet -> ? -> unreconciled
    ("2026/12/05", "CASH DEP", "250.00"),                # client money nobody can place -> unreconciled, stays
    ("2026/12/05", "MYSTERY", "75.00"),                  # head coach not sure yet -> hold
]
BANK_2_NEW = [
    ("2026/12/09", "ZANELE DUBE", "500.00"),             # rest of HN-0002
    ("2026/12/10", "IVAN PETROV", "1100.00"),            # overpaid by 50 -> invoice paid, R50 listed for Morgan
    ("2026/12/11", "2026 #4 PAYMENT", "350.00"),
    ("2026/12/11", "BS 04-102", "900.00"),               # Dineo's 2026-04-102, year left off         # printed number Fatima AND Gareth both use -> never auto-paid
]


def run(*args, ok=(0,)):
    env = dict(os.environ, CRM_TODAY=os.environ.get("CRM_TODAY", "2026-12-05"))
    p = subprocess.run([sys.executable, *args], cwd=REPO, capture_output=True, text=True, env=env)
    if p.returncode not in ok:
        raise AssertionError(f"{args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p.returncode, p.stdout


def write_bank(path, lines):
    """The statement as the bank gives it, and the lines the head coach's Claude reads from it into hub/bank/lines/."""
    read = []
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Amount", "Balance"])
        balance = 10000
        for d, desc, amt in lines:
            balance += float(amt)
            w.writerow([d, desc, amt, f"{balance:.2f}"])
            read.append([d.replace("/", "-"), desc, amt, f"{balance:.2f}"])
    with (path.parent / "lines" / f"{path.name}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "description", "amount", "balance"])
        w.writerows(read)


def issue_list(root, slug, period, issued, rows):
    """What the invoice generator does at issue: the PDFs (stand-ins here), then one sealed list Sheet per run."""
    folder = root / f"coach-{slug}"
    for r in rows:
        r["pdf"] = f"invoices/{period}/{r['number']}.pdf"
        (folder / r["pdf"]).parent.mkdir(parents=True, exist_ok=True)
        (folder / r["pdf"]).write_bytes(f"%PDF stand-in for {r['number']}".encode())
        r["pdf_sha"] = file_hash(folder / r["pdf"])
        r["pdf_bytes"] = (folder / r["pdf"]).stat().st_size
    rows = [{c: str(r.get(c, "")) for c in LIST_COLS} for r in rows]
    meta = {"coach": slug, "period": period, "issued": issued}
    write_sheet(folder / "invoice-lists" / f"{period}.csv", LIST_COLS, rows, title=f"Invoice list: {slug}, {period}",
                meta=dict(meta, made_by=GENERATOR, seal=list_seal(meta, rows)))


def november_rows(slug):
    code = dict((s, c) for s, c, _ in COACHES)[slug]
    return [{"number": f"{code}-{i:04d}", "date": "2026-12-01", "client_id": cid, "client": name, "payer": payer,
             # Dineo's invoices use the real format (year-coach number-invoice number)
             "reference": f"2026-04-10{i}" if slug == "dineo" else f"{code}-{i:04d}",
             "amount": f"{amt}.00", "applies_to": "", "pdf": f"{code}-{i:04d}.pdf"}
            for i, (cid, name, payer, amt) in enumerate(CLIENTS[slug], 1)]


def decide(path, decisions):
    """Pick decisions in a proposal Sheet the way the head coach does: by line number."""
    _, rows = read_sheet(path)
    for r in rows:
        if r["line"] in decisions:
            r.update(decisions[r["line"]])
    rewrite_table(path, list(rows[0].keys()), rows)


def find(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def section(text, heading):
    return text.split(f"## {heading}")[1].split("\n## ")[0]


class Cycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.root = cls.tmp / "Test CRM"
        shutil.copytree(REPO / "_templates" / "drive", cls.root)
        shutil.rmtree(cls.root / "coach-template")
        (cls.root / "factory/business.txt").write_text("trading_name: Example Coaching Co\ncurrency_symbol: R\n"
                                                    "invoice_number_format: \"{year}-{coach}-{seq}\"\ninvoice_day: 24\n")
        cls.R = ["--root", str(cls.root)]
        for slug, code, name in COACHES:                    # the head coach adds each coach: next coach number
            run("scripts/coaches.py", *cls.R, "add", "--name", name, "--code", code, "--phone", f"+2782000{len(slug):04d}",
                "--email", f"{slug}@example.test")
        clients = [{"id": cid, "name": cname, "phone": f"0820000{cid[1:]}", "email": "", "status": "active",
                    "coach": slug, "since": "2026-11-01", "notes": ""}
                   for slug, _, _ in COACHES for cid, cname, _, _ in CLIENTS[slug]]
        append_rows(cls.root / "hub/clients.csv", ["id", "name", "phone", "email", "status", "coach", "since", "notes"], clients)
        cls.R = ["--root", str(cls.root)]

    @classmethod
    def tearDownClass(cls):
        if os.environ.get("KEEP"):
            print(f"\nKept test drive at {cls.root}")
        else:
            shutil.rmtree(cls.tmp)

    def coach_file(self, slug, name):
        return (self.root / f"coach-{slug}" / name).read_text()

    def hub_file(self, name):
        return (self.root / "hub" / name).read_text()

    def test_cycle(self):
        R = self.R
        # --- coach numbers: 01-08, in the order the head coach added them, each in that coach's own me Doc ---
        coaches = read_table(self.root / "hub/coaches.csv")
        self.assertEqual([(c["number"], c["slug"]) for c in coaches], [(f"{i:02d}", s) for i, (s, _, _) in enumerate(COACHES, 1)])
        self.assertIn('coach_number: 06', self.coach_file("fatima", "me.txt"))
        # --- client lists: each coach gets only their own ---
        run("scripts/build_lists.py", *R, "coach-clients")
        for slug, _, _ in COACHES:
            text = self.coach_file(slug, "clients.csv")
            for other, clist in CLIENTS.items():
                for cid, _, _, _ in clist:
                    self.assertEqual(cid in text, other == slug, f"{cid} in {slug}'s clients.csv")

        # --- invoicing run: a coach is done when their invoice list exists ---
        _, out = run("scripts/runs.py", *R, "open", "2026-11")
        self.assertIn("due 2026-11-24", out)              # invoice_day from factory/business.md
        for slug, _, _ in COACHES:                        # the head coach's side makes every coach's month folder
            self.assertTrue((self.root / f"coach-{slug}/invoices/2026-11").is_dir(), slug)
        for slug in ["morgan", "ayanda", "ben", "fatima", "hannah"]:
            issue_list(self.root, slug, "2026-11", "2026-12-01", november_rows(slug))
        _, out = run("scripts/runs.py", *R, "status", "2026-11")
        self.assertIn("5 of 8 done", out)
        self.assertIn("NOT DONE  Gareth", out)
        self.assertRegex(out, r"done\s+Ayanda\s+3 invoices\s+3520.00")
        _, out = run("scripts/recon.py", *R, "bank", "--month-end", "2026-11", ok=(3,))
        self.assertIn("GATE: not complete", out)
        self.assertFalse(list((self.root / "hub/recon").glob("*.csv")), "gate must stop before any proposal")
        for slug in ["gareth", "dineo", "ethan"]:
            issue_list(self.root, slug, "2026-11", "2026-12-03", november_rows(slug))
        _, out = run("scripts/runs.py", *R, "status", "2026-11")
        self.assertIn("8 of 8 done — COMPLETE", out)

        # --- recon 1 ---
        write_bank(self.root / "hub/bank/2026-12-05.csv", BANK_1)
        run("scripts/recon.py", *R, "bank", "--month-end", "2026-11")
        prop = self.root / "hub/recon/bank-2026-12-05.csv"
        rows = read_table(prop)
        self.assertEqual(len(read_table(self.root / "hub/eft-ledger.csv")), 16, "16 incoming; bank fees ignored")
        self.assertEqual(find(rows, invoice="AY-0001")[0]["confidence"], "reference")
        self.assertEqual(find(rows, invoice="AY-0002")[0]["confidence"], "name + amount")
        self.assertEqual(find(rows, description="R KHAN")[0]["invoice"], "ET-0002")     # matched on the payer
        split = find(rows, description="MOKOENA")
        self.assertEqual({(r["invoice"], r["amount"]) for r in split}, {("BN-0003", "700.00"), ("HN-0001", "560.00")})
        samson = find(rows, description="SAMSON T")
        self.assertEqual({(r["kind"], r["amount"]) for r in samson}, {("payment", "1400.00"), ("overpayment", "100.00")})
        self.assertEqual(find(rows, description="SMITH")[0]["invoice"], "GR-0003")
        self.assertEqual(find(rows, description="KP BN 0001")[0]["invoice"], "BN-0001")
        must_decide = {r["description"] for r in rows if r["decision"] == "?"}
        self.assertEqual(must_decide, {"COACHING", "TRANSFER FROM SAVINGS", "ZANELE DUBE", "PV HN 3", "PREPAY JANE",
                                       "CASH DEP", "MYSTERY"})

        _, out = run("scripts/recon.py", *R, "push", str(prop), ok=(1,))
        self.assertIn("undecided", out)                   # every unplaced EFT needs the head coach

        line = {r["description"]: r["line"] for r in rows}
        decide(prop, {line["COACHING"]: {"coach": "gareth", "client_id": "C0013", "invoice": "GR-0001", "decision": "accept"},
                      line["TRANSFER FROM SAVINGS"]: {"decision": "non-client"},
                      line["ZANELE DUBE"]: {"decision": "accept"},
                      line["PV HN 3"]: {"decision": "unreconciled"},
                      line["PREPAY JANE"]: {"decision": "unreconciled"},
                      line["CASH DEP"]: {"decision": "unreconciled"},
                      line["MYSTERY"]: {"decision": "hold"}})
        _, out = run("scripts/recon.py", *R, "push", str(prop))
        self.assertIn("Unreconciled live list: 3 payment(s), 1800.00", out)
        run("scripts/recon.py", *R, "push", str(prop), ok=(2,))   # can't push twice

        unrec = self.hub_file("unreconciled.csv")
        live = section(unrec, "Client money, not yet matched (live list)")
        for desc in ("PV HN 3", "PREPAY JANE", "CASH DEP"):
            self.assertIn(desc, live)
        self.assertNotIn("SAVINGS", unrec)                # non-client drops out
        self.assertIn("MYSTERY", section(unrec, "Not yet reviewed"))

        self.assertIn("BN-0002", self.coach_file("ben", "unpaid.csv"))
        self.assertNotIn("BN-0003", self.coach_file("ben", "unpaid.csv"))
        hannah = self.coach_file("hannah", "unpaid.csv")
        self.assertIn("HN-0002,2026-12-01,C0008,Zanele Dube,,900.00,500.00,4,HN-0002", hannah)
        # Morgan sees every coach's unpaid invoices, with days unpaid, in one list
        self.assertIn("hannah,HN-0003,2026-12-01,C0009,Peter Venter,1050.00,1050.00,4,HN-0003",
                      section(self.hub_file("summary.csv"), "Unpaid invoices"))
        self.assertNotIn("C0016", self.coach_file("fatima", "unpaid.csv"))   # paid; the R100 extra is Morgan's to handle
        self.assertIn("fatima,C0016,FT-0001,100.00", self.hub_file("summary.csv"))
        self.assertIn("HN-0003", hannah)                  # Peter paid, but nobody knows yet

        # --- recon 2, proof of payment: Hannah chases Peter, he sends a POP, Hannah uploads it to her pops/ ---
        PETER, UNKNOWN, MYSTERY = "coach-hannah/pops/HN-0003 Peter.pdf", "coach-gareth/pops/naidoo.pdf", "hub/pops/mystery.pdf"
        for path in (PETER, UNKNOWN, MYSTERY):
            (self.root / path).write_text("(made-up POP)")
        _, out = run("scripts/recon.py", *R, "pops")
        self.assertIn("3 POP file(s) aren't in the register", out)          # read them first
        append_rows(self.root / "hub/pop-register.csv", ["file", "read_on", "date", "amount", "payer", "reference", "client", "invoice"], [
            {"file": PETER, "read_on": "2026-12-08", "date": "2026-12-05", "amount": "1050.00",   # invoice from the file name
             "payer": "P Venter", "reference": "PV HN 3", "client": "Peter Venter", "invoice": ""},
            {"file": UNKNOWN, "read_on": "2026-12-09", "date": "2026-12-08", "amount": "820.00",
             "payer": "S Naidoo", "reference": "LESSONS", "client": "", "invoice": ""},
            {"file": MYSTERY, "read_on": "2026-12-09", "date": "2026-12-05", "amount": "75.00",
             "payer": "M Ystery", "reference": "MYSTERY", "client": "", "invoice": ""}])
        _, out = run("scripts/recon.py", *R, "pops")
        pop_prop = self.root / "hub/recon/pop-2026-12-05.csv"
        rows = read_table(pop_prop)
        peter = find(rows, pop=PETER)[0]
        self.assertEqual((peter["description"], peter["invoice"], peter["decision"]), ("PV HN 3", "HN-0003", "accept"))
        self.assertEqual(find(rows, pop=UNKNOWN)[0]["decision"], "hold")      # no such payment in the bank
        # MYSTERY was held at the bank recon, so it isn't on the live list: the POP recon may not touch it
        self.assertEqual(find(rows, pop=MYSTERY)[0]["decision"], "hold")
        _, out = run("scripts/recon.py", *R, "push", str(pop_prop))
        self.assertIn("Unreconciled live list: 2 payment(s), 750.00", out)
        self.assertNotIn("HN-0003", self.coach_file("hannah", "unpaid.csv"))
        waiting = section(self.hub_file("unreconciled.csv"), "Proofs of payment waiting")
        self.assertIn("naidoo", waiting)
        self.assertNotIn("Peter", waiting)
        _, out = run("scripts/recon.py", *R, "pops")                               # Peter's POP isn't offered again
        bad = self.root / "hub/recon/pop-2026-12-05-2.csv"
        self.assertNotIn("Peter", bad.read_text())

        # a POP proposal can't be pointed at money that isn't on the live list ...
        ledger = read_table(self.root / "hub/eft-ledger.csv")
        mystery_eft = next(e["eft_id"] for e in ledger if e["description"] == "MYSTERY")
        line = find(read_table(bad), pop=MYSTERY)[0]["line"]
        decide(bad, {line: {"eft_id": mystery_eft, "coach": "ayanda", "client_id": "C0003", "invoice": "AY-0003",
                            "amount": "75.00", "decision": "accept"}})
        _, out = run("scripts/recon.py", *R, "push", str(bad), ok=(1,))
        self.assertIn("isn't on the unreconciled list", out)
        # ... and a POP Gareth uploaded can't settle another coach's invoice
        cash_eft = next(e["eft_id"] for e in ledger if e["description"] == "CASH DEP")
        decide(bad, {line: {"decision": "hold"}})
        gline = find(read_table(bad), pop=UNKNOWN)[0]["line"]
        decide(bad, {gline: {"eft_id": cash_eft, "coach": "hannah", "client_id": "C0008", "invoice": "HN-0002",
                             "amount": "250.00", "decision": "accept"}})
        _, out = run("scripts/recon.py", *R, "push", str(bad), ok=(1,))
        self.assertIn("was uploaded by gareth, not hannah", out)
        decide(bad, {gline: {"decision": "hold"}})
        run("scripts/recon.py", *R, "push", str(bad))

        # --- write-off, agreed directly between Ben and Morgan ---
        run("scripts/recon.py", *R, "write-off", "BN-0002", "--reason", "client moved away")
        self.assertIn("Outstanding: 0.00", self.coach_file("ben", "unpaid.csv"))

        # --- confidentiality: no coach file shows another coach's invoices or clients, or non-client money ---
        for slug, code, _ in COACHES:
            self.assertEqual(sorted(p.name for p in (self.root / f"coach-{slug}").iterdir() if p.is_file()),
                             ["clients.csv", "me.txt", "unpaid.csv"], "a coach gets no payment file")
            text = "".join(self.coach_file(slug, f) for f in ("clients.csv", "unpaid.csv"))
            for other, ocode, _ in COACHES:
                if other == slug:
                    continue
                self.assertNotIn(f"{ocode}-0", text, f"{other}'s invoice in {slug}'s folder")
                for cid, _, _, _ in CLIENTS[other]:
                    self.assertNotIn(cid, text, f"{other}'s client {cid} in {slug}'s folder")
            for hub_only in ("SAVINGS", "PREPAY", "CASH DEP", "MYSTERY", "PV HN", "COACHING",
                             "2026-12-02", "2026-12-03", "2026-12-04",   # bank payment dates
                             "proof of payment matched", "write-off"):
                self.assertNotIn(hub_only, text)

        # --- a regular Claude chat (outside the Project) messes with Gareth's folder: all of it is caught ---
        self.assertIn("GR-0002", [r["number"] for r in read_table(self.root / "hub/all-invoices.csv")])  # Morgan's copy
        gar = self.root / "coach-gareth"
        nov = gar / "invoice-lists/2026-11.csv"
        original = nov.read_text()
        nov.write_text(original.replace("GR-0002,2026-12-01,C0014,Lisa Smith,,GR-0002,1400.00",
                                        "GR-0002,2026-12-01,C0014,Lisa Smith,,GR-0002,14.00"))     # cut 1400 to 14
        (gar / "invoice-lists/2026-11-extra.csv").write_text("coach:,gareth\nperiod:,2026-11\n\nnumber,amount\nGR-9999,999.00\n")
        (gar / "invoices/2026-11/Invoice made in chat.pdf").write_bytes(b"%PDF hand-made")
        (gar / "my notes.txt").write_text("stray")
        _, out = run("scripts/build_lists.py", *R, "books")
        summary = section(self.hub_file("summary.csv"), "Folder checks")
        for expected in ("coach-gareth/invoice-lists/2026-11 was changed after the head coach's copy was taken; the copy is used",
                         "coach-gareth/invoice-lists/2026-11-extra wasn't made by the invoice generator",
                         "coach-gareth/invoices/2026-11/Invoice made in chat.pdf isn't on any of the coach's invoice lists",
                         "coach-gareth/my notes.txt shouldn't be here"):
            self.assertIn(expected, summary)
        owed = section(self.coach_file("gareth", "unpaid.csv"), "Unpaid invoices")
        self.assertNotIn("GR-9999", owed)                                     # an unsealed list is never trusted
        self.assertIn("GR-0002,2026-12-01,C0014,Lisa Smith,,1400.00,1400.00", owed)   # Morgan's copy wins, not the 14.00
        self.assertNotIn("GR-0002.pdf", summary)                              # its real PDFs aren't called strays
        self.assertIn("⚠ invoice-lists/2026-11 was changed after the head coach's copy was taken",
                      self.coach_file("gareth", "unpaid.csv"))
        self.assertNotIn("coach-gareth", self.coach_file("ayanda", "unpaid.csv"))   # other coaches aren't told
        _, out = run("scripts/runs.py", *R, "status", "2026-11")
        self.assertIn("NOT DONE  Gareth", out)                                # a changed list doesn't count as done
        # Morgan restores the list (Drive version history) and the stray files are removed: all clear again
        nov.write_text(original)
        for stray in ("invoice-lists/2026-11-extra.csv", "invoices/2026-11/Invoice made in chat.pdf", "my notes.txt"):
            (gar / stray).unlink()
        run("scripts/build_lists.py", *R, "books")
        self.assertIn("# None.", section(self.hub_file("summary.csv"), "Folder checks"))
        self.assertNotIn("⚠", self.coach_file("gareth", "unpaid.csv"))
        _, out = run("scripts/runs.py", *R, "status", "2026-11")
        self.assertIn("8 of 8 done", out)
        # even a list deleted outright is no loss: Morgan's copy keeps it
        nov.unlink()
        run("scripts/build_lists.py", *R, "books")
        self.assertIn("coach-gareth/invoice-lists/2026-11 is missing from the coach's folder; the head coach's copy is used",
                      self.hub_file("summary.csv"))
        self.assertIn("GR-0002", self.coach_file("gareth", "unpaid.csv"))
        nov.write_text(original)
        run("scripts/build_lists.py", *R, "books")

        # --- December: new lists, then a follow-up recon on an overlapping export ---
        issue_list(self.root, "fatima", "2026-12", "2026-12-08", [
            {"number": "FT-0004", "date": "2026-12-08", "client_id": "C0016", "client": "Samson Tau", "payer": "",
             "reference": "2026 #4", "amount": "350.00", "applies_to": "", "pdf": "FT-0004.pdf"}])
        issue_list(self.root, "ayanda", "2026-12", "2026-12-08", [
            {"number": "AY-0004", "date": "2026-12-08", "client_id": "C0025", "client": "Jane Doe", "payer": "",
             "reference": "AY-0004", "amount": "500.00", "applies_to": "", "pdf": "AY-0004.pdf"}])
        issue_list(self.root, "gareth", "2026-12", "2026-12-08", [
            {"number": "GR-0004", "date": "2026-12-08", "client_id": "C0013", "client": "Jabu Nkosi", "payer": "",
             "reference": "2026 #4", "amount": "350.00", "applies_to": "", "pdf": "GR-0004.pdf"}])
        os.environ["CRM_TODAY"] = "2026-12-12"
        try:
            write_bank(self.root / "hub/bank/2026-12-12.csv", BANK_1 + BANK_2_NEW)
            _, out = run("scripts/recon.py", *R, "bank")
            self.assertIn("New bank lines: 4", out)       # the 16 old lines were skipped
            prop2 = self.root / "hub/recon/bank-2026-12-12.csv"
            rows = read_table(prop2)
            self.assertEqual({(r["kind"], r["amount"]) for r in find(rows, description="IVAN PETROV")},
                             {("payment", "1050.00"), ("overpayment", "50.00")})
            self.assertEqual(find(rows, description="ZANELE DUBE")[0]["invoice"], "HN-0002")
            self.assertEqual(find(rows, description="PREPAY JANE")[0]["invoice"], "AY-0004")   # live list item now matches
            self.assertFalse(find(rows, description="CASH DEP"), "live list items with no new match aren't re-asked")
            self.assertEqual(find(rows, description="MYSTERY")[0]["decision"], "?")              # held, so asked again

            short = find(rows, description="BS 04-102")[0]
            self.assertEqual((short["invoice"], short["confidence"]), ("DN-0002", "reference"))
            shared = find(rows, description="2026 #4 PAYMENT")[0]
            self.assertEqual((shared["confidence"], shared["decision"]), ("reference fits several coaches", "?"))
            decide(prop2, {shared["line"]: {"decision": "hold"}})
            before = self.hub_file("allocations.csv")
            mystery = find(rows, description="MYSTERY")[0]["line"]
            decide(prop2, {mystery: {"coach": "ben", "client_id": "C0001", "invoice": "AY-0003", "amount": "75.00",
                                     "decision": "accept"}})
            _, out = run("scripts/recon.py", *R, "push", str(prop2), ok=(1,))
            self.assertIn("belongs to ayanda/C0003", out)  # a wrong-coach decision is refused, nothing written
            self.assertEqual(before, self.hub_file("allocations.csv"))

            decide(prop2, {mystery: {"decision": "non-client"}})
            _, out = run("scripts/recon.py", *R, "push", str(prop2))
            self.assertIn("Unreconciled live list: 1 payment(s), 250.00", out)   # only CASH DEP left

        finally:
            os.environ.pop("CRM_TODAY", None)

        fat = self.coach_file("fatima", "unpaid.csv")
        self.assertIn("2026 #4,2026-12-08,C0016,Samson Tau,,350.00,350.00,4,FT-0004", fat)  # no credit in this system
        self.assertNotIn("Credit", fat)
        self.assertIn("morgan,C0024,CH-0003,50.00", self.hub_file("summary.csv"))
        self.assertNotIn("HN-0002", self.coach_file("hannah", "unpaid.csv"))
        self.assertNotIn("AY-0004", self.coach_file("ayanda", "unpaid.csv"))
        self.assertIn("Unreconciled live list: 1 payment(s), 250.00", self.hub_file("summary.csv"))


        # --- a client moves coach: both client lists update by themselves; the open invoice stays put ---
        main = self.root / "hub/clients.csv"
        main.write_text(main.read_text().replace("C0019,Lindiwe Mabaso,08200000019,,active,dineo",
                                                 "C0019,Lindiwe Mabaso,08200000019,,active,ethan"))
        _, out = run("scripts/build_lists.py", *R, "coach-clients")
        self.assertIn("Changed: dineo, ethan", out)
        self.assertIn("C0019", self.coach_file("ethan", "clients.csv"))
        self.assertNotIn("C0019", self.coach_file("dineo", "clients.csv"))
        self.assertIn("DN-0001", self.coach_file("dineo", "unpaid.csv"))      # Dineo taught those lessons
        self.assertNotIn("DN-0001", self.coach_file("ethan", "unpaid.csv"))

        # --- even if the main list changes some other way, the next recon step refreshes the coach lists ---
        main.write_text(main.read_text().replace("C0021,Grace Nel,08200000021,,active",
                                                 "C0021,Grace Nel,08200000021,,left"))
        run("scripts/recon.py", *R, "write-off", "DN-0003", "--reason", "left")
        self.assertNotIn("C0021", self.coach_file("dineo", "clients.csv"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
