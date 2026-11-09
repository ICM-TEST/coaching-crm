"""The books: invoice balances, EFT states, the head coach's copy of every invoice, and the generated views.

Hub Sheets hold every money fact, each with one job:
  eft-ledger      what came into the bank
  eft-reviews     the head coach's verdict on money the recon couldn't place: client or not
  allocations     which invoice each rand went to (or that it was an overpayment)
  all-invoices    the head coach's own copy of every sealed invoice row, taken the first time a recon sees it
Each coach's unpaid Sheet is a projection of the invoices minus allocations, filtered to that coach. That filter
keeps one coach's money out of another's folder, and the projection shows only paid-or-not.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .common import (ZERO, Drive, append_rows, coach_me, days_between, fmt, frontmatter, iso_date, me_name,
                     money, read_sheet, read_table, today, write_generated)

ALLOC_COLUMNS = ["id", "date", "recon", "eft_id", "coach", "client_id", "invoice", "amount", "kind", "note"]
LEDGER_COLUMNS = ["eft_id", "date", "amount", "description", "source"]
REVIEW_COLUMNS = ["eft_id", "date", "verdict", "recon"]
POP_COLUMNS = ["file", "read_on", "date", "amount", "payer", "reference", "client", "invoice"]
LIST_COLUMNS = ["number", "date", "client_id", "client", "payer", "reference", "amount", "applies_to", "pdf",
                "pdf_sha", "pdf_bytes"]
ARCHIVE_COLUMNS = ["coach", "list", "seal", "archived"] + LIST_COLUMNS
REDUCES_INVOICE = {"payment", "write-off"}

GENERATOR = "issue.py"
IGNORED = {"desktop.ini", "Icon\r"}                  # files Drive or the OS may add on their own
INDEX = ".drive-index.csv"                           # path · size: what's on the drive but not downloaded (connector mode)


def file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _norm(column: str, value: str) -> str:
    """One spelling per value, however a Sheet hands it back (1440 / 1,440.00; 24/10/2026), so seals survive."""
    v = str(value or "").strip()
    if not v:
        return ""
    try:
        if column in ("amount",):
            return fmt(money(v))
        if column in ("date", "issued"):
            return iso_date(v)
        if column in ("pdf_bytes",):
            return str(int(float(v)))
    except (ValueError, ArithmeticError):
        pass
    return v


def list_seal(meta: dict, rows: list[dict]) -> str:
    """The invoice generator's seal on a list: changes if anything in the list changes after issue."""
    payload = {"coach": meta.get("coach", ""), "period": meta.get("period", ""),
               "issued": _norm("issued", meta.get("issued", "")),
               "rows": [{c: _norm(c, r.get(c, "")) for c in LIST_COLUMNS} for r in rows]}
    return "seal-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _list_order(path: Path) -> tuple:
    """2026-10 before 2026-10-2 before 2026-10-10. Plain name order would put 2026-10-2 first."""
    m = re.fullmatch(r"(\d{4}-\d{2})(?:-(\d+))?", path.stem)
    return (m.group(1), int(m.group(2) or 1)) if m else (path.stem, 0)


def invoice_lists(folder) -> list[tuple[dict, list[dict]]]:
    """(preamble, rows) for every list Sheet in a coach's invoice-lists/. Sheets without a period aren't lists.

    meta["problem"] is set when a list wasn't made by the invoice generator, or was changed after issue, e.g. by
    a Claude chat outside the coach's Project. Such a list is never trusted: callers leave its invoices out."""
    out = []
    for path in sorted((folder / "invoice-lists").glob("*.csv"), key=_list_order):   # issue order: an update comes last
        meta, rows = read_sheet(path)
        if not meta.get("period"):
            continue
        problem = ""
        if meta.get("made_by") != GENERATOR or not meta.get("seal"):
            problem = "wasn't made by the invoice generator"
        elif meta["seal"] != list_seal(meta, rows):
            problem = "was changed after it was issued"
        out.append((dict(meta, file=path.stem, problem=problem), rows))
    return out


def drive_index(root: Path) -> dict[str, str]:
    """path -> size, for files listed through the connector but not downloaded (PDFs, mostly)."""
    return {r["path"]: r.get("size", "") for r in read_table(Path(root) / INDEX)}


def audit_coach_folder(folder: Path, lists: list[tuple[dict, list[dict]]], index: dict[str, str]) -> list[str]:
    """Anything in a coach's folder that the system didn't put there, or that changed since. Checked at every recon."""
    problems = []
    slug_dir = folder.name
    expected = {r.get("pdf", ""): r for m, rows in lists for r in rows}   # a changed list's PDFs aren't strays
    local = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}
    remote = {k[len(slug_dir) + 1:] for k in index if k.startswith(slug_dir + "/")}
    for rel in sorted(local | remote):
        name, top = rel.rsplit("/", 1)[-1], rel.split("/", 1)[0]
        if name.startswith(".") or name in IGNORED or top == "pops":
            continue                                        # POPs: the coach uploads whatever the client sent
        if rel in (me_name(slug_dir.removeprefix("coach-")), "clients.csv", "unpaid.csv", "invoice-lists/README.txt"):
            continue
        if top == "invoice-lists" and rel.endswith(".csv"):
            continue                                        # judged by its seal, in invoice_lists()
        if top == "invoices" and rel.endswith(".pdf"):
            row = expected.get(rel)
            if row is None:
                problems.append(f"{rel} isn't on any of the coach's invoice lists (not made by the invoice generator?)")
            elif rel in local and row.get("pdf_sha") and file_hash(folder / rel) != row["pdf_sha"]:
                problems.append(f"{rel} was changed after it was issued")
            elif rel not in local and row.get("pdf_bytes") and _norm("pdf_bytes", index.get(f"{slug_dir}/{rel}", "")) \
                    != _norm("pdf_bytes", row["pdf_bytes"]):
                problems.append(f"{rel} was changed after it was issued (its size doesn't match)")
            continue
        problems.append(f"{rel} shouldn't be here: the coach's folder only holds invoice lists, PDFs and POPs")
    for rel in expected:
        if rel and rel not in local and rel not in remote:
            problems.append(f"{rel} is on an invoice list but missing")
    return problems


class Books:
    def __init__(self, drive: Drive):
        self.drive = drive
        self.allocations = read_table(drive.hub / "allocations.csv")
        self.ledger = [dict(e, date=iso_date(e["date"])) for e in read_table(drive.hub / "eft-ledger.csv")]
        self.verdicts = {r["eft_id"]: r["verdict"] for r in read_table(drive.hub / "eft-reviews.csv")}  # latest wins
        self.invoices: dict[str, dict] = {}          # number -> invoice row (+ coach)
        self.updates: list[dict] = []                # invoices a coach re-issued with a new amount, for the summary
        self.lists_seen: dict[str, set] = defaultdict(set)      # coach -> lists these books include
        self.problems: list[str] = []
        self.coach_problems: dict[str, list[str]] = defaultdict(list)   # shown to that coach, and to the head coach
        self.to_archive: list[dict] = []             # sealed rows seen for the first time: copied to all-invoices
        numbers: dict[str, list[str]] = defaultdict(list)       # coach number -> coaches: must be one each
        for c in drive.coaches(active_only=False):
            numbers[str(c.get("number", "")).strip().zfill(2)].append(c["slug"])
        for no, slugs in numbers.items():
            if no.strip("0") and len(slugs) > 1:
                self.problems.append(f"coach number {no} is used by {', '.join(slugs)}: each coach needs their own")

        # 1. the head coach's copy is the record
        archive = read_table(drive.hub / "all-invoices.csv")
        archived = {(r["coach"], r["list"]): r["seal"] for r in archive}
        for r in archive:
            self._add(dict(r, date=iso_date(r["date"])), r["coach"], r["list"])
        # 2. coach lists: new sealed ones are added (and copied); changed or unsealed ones are reported
        index = drive_index(drive.root)
        for slug in drive.all_coach_slugs():
            folder = drive.coach_dir(slug)
            lists = invoice_lists(folder)
            seen = set()
            for meta, rows in lists:
                key = (slug, meta["file"])
                seen.add(meta["file"])
                if key in archived:
                    if meta["problem"] or meta["seal"] != archived[key]:
                        self.coach_problems[slug].append(
                            f"invoice-lists/{meta['file']} was changed after the head coach's copy was taken; the copy is "
                            "used (restore the list from its version history)")
                    continue
                if meta["problem"]:
                    self.coach_problems[slug].append(
                        f"invoice-lists/{meta['file']} {meta['problem']}, so its invoices are left out until it's sorted "
                        "out (restore it from the file's version history, or re-issue)")
                    continue
                for row in rows:
                    row = dict(row, date=iso_date(row["date"]), amount=_norm("amount", row["amount"]))
                    self._add(row, slug, meta["file"])
                    self.to_archive.append(dict(row, coach=slug, list=meta["file"], seal=meta["seal"],
                                                archived=today()))
            on_drive = {k.split("/")[-1].rsplit(".", 1)[0] for k in index if k.startswith(f"coach-{slug}/invoice-lists/")}
            for (c, lst) in archived:
                if c == slug and lst not in seen and lst not in on_drive:
                    self.coach_problems[slug].append(f"invoice-lists/{lst} is missing from the coach's folder; the head "
                                                     "coach's copy is used")
            self.coach_problems[slug] += audit_coach_folder(folder, lists, index)
        self.problems += [f"coach-{slug}/{m}" for slug, ms in sorted(self.coach_problems.items()) for m in ms]
        for u in self.updates:                                  # lowered below what was already paid: the head coach's to sort
            if self.invoices[u["number"]]["list"] == u["list"] and self.balance(u["number"]) < ZERO:
                self.problems.append(f"{u['invoice']} ({u['coach']}) was updated to {u['now']}, below the "
                                     f"{fmt(self.paid_on(u['number']))} already paid")

    def _add(self, row: dict, coach: str, lst: str) -> None:
        row = dict(row, coach=coach, list=lst)
        self.lists_seen[coach].add(lst)
        current = self.invoices.get(row["number"])
        if not current:
            self.invoices[row["number"]] = row
        elif row.get("applies_to") == row["number"]:            # a sealed update: its amount replaces the old one
            self.updates.append({"coach": coach, "number": row["number"], "invoice": row.get("reference") or row["number"],
                                 "client": row.get("client", ""), "was": current["amount"], "now": row["amount"],
                                 "list": lst})
            self.invoices[row["number"]] = row
        elif current["list"] != lst:
            self.problems.append(f"{row['number']} appears twice ({current['list']}, {lst}) "
                                 f"in {coach}'s lists; the first is used")

    def archive_new(self) -> int:
        """Copy newly seen sealed invoice rows into the head coach's all-invoices Sheet (appended, never edited)."""
        append_rows(self.drive.hub / "all-invoices.csv", ARCHIVE_COLUMNS, self.to_archive)
        n, self.to_archive = len(self.to_archive), []
        return n

    # ----- invoices -----

    def paid_on(self, number: str) -> Decimal:
        return sum((money(a["amount"]) for a in self.allocations
                    if a.get("invoice") == number and a.get("kind") in REDUCES_INVOICE), ZERO)

    def balance(self, number: str) -> Decimal:
        return money(self.invoices[number]["amount"]) - self.paid_on(number)

    def open_invoices(self, coach: str | None = None) -> list[dict]:
        out = []
        for number, inv in self.invoices.items():
            if coach and inv["coach"] != coach:
                continue
            bal = self.balance(number)
            if bal > ZERO:
                out.append(dict(inv, balance=bal, paid=self.paid_on(number)))
        return sorted(out, key=lambda r: (r["date"], r["number"]))

    # ----- overpayments -----

    def overpayments(self) -> list[dict]:
        """Money paid beyond an invoice. Not tracked as credit here: the head coach handles it in their own accounting."""
        return [a for a in self.allocations if a.get("kind") == "overpayment"]

    # ----- EFTs -----

    def remaining(self, eft: dict) -> Decimal:
        used = sum((money(a["amount"]) for a in self.allocations if a.get("eft_id") == eft["eft_id"]), ZERO)
        return money(eft["amount"]) - used

    def open_efts(self) -> list[dict]:
        """Money not yet placed, and not judged non-client. state: 'unreconciled' (verified client money) or 'unreviewed'."""
        out = []
        for e in self.ledger:
            verdict = self.verdicts.get(e["eft_id"])
            rem = self.remaining(e)
            if verdict == "non-client" or rem <= ZERO:
                continue
            out.append(dict(e, remaining=rem, state="unreconciled" if verdict == "client" else "unreviewed"))
        return sorted(out, key=lambda r: (r["date"], r["eft_id"]))

    def eft(self, eft_id: str) -> dict | None:
        return next((e for e in self.ledger if e["eft_id"] == eft_id), None)

    # ----- proofs of payment -----

    def pops_used(self) -> set[str]:
        return {a["recon"][4:] for a in self.allocations if a.get("recon", "").startswith("pop:")}

    def pop_register(self) -> list[dict]:
        return read_table(self.drive.hub / "pop-register.csv")

    def pop_files(self) -> list[str]:
        """Every POP on the drive, as a path from the drive root. Coaches upload their clients' POPs to
        their own coach-<slug>/pops/; anything the head coach receives directly goes in hub/pops/."""
        folders = [self.drive.hub / "pops"] + [self.drive.coach_dir(s) / "pops" for s in self.drive.all_coach_slugs()]
        local = {str(p.relative_to(self.drive.root)) for f in folders if f.is_dir() for p in f.iterdir()
                 if p.is_file() and not p.name.startswith(".") and p.name != "README.txt"}
        remote = {k for k in drive_index(self.drive.root)                    # listed through the connector
                  if (k.startswith("hub/pops/") or (k.startswith("coach-") and "/pops/" in k))
                  and not k.endswith("README.txt")}
        return sorted(local | remote)

    @staticmethod
    def pop_coach(path: str) -> str:
        """The coach who uploaded a POP (from its folder), or '' if it came to the head coach directly."""
        top = path.split("/", 1)[0]
        return top[len("coach-"):] if top.startswith("coach-") else ""

    def pops_waiting(self) -> list[dict]:
        """POPs not yet used by a POP recon: read into the register, or not read yet."""
        used, register = self.pops_used(), self.pop_register()
        rows = [dict(r, state="read") for r in register if r["file"] not in used]
        read = {r["file"] for r in register}
        rows += [{"file": f, "state": "not read yet"} for f in self.pop_files() if f not in read]
        return rows

    def client_name(self, coach: str, client_id: str) -> str:
        for inv in self.invoices.values():
            if inv["coach"] == coach and inv["client_id"] == client_id:
                return inv.get("client", "")
        return ""


# ---------- generated views ----------

CLIENT_COLUMNS = ["id", "name", "phone", "email", "status", "since"]
ME_FIELDS = [("name", "name"), ("slug", "slug"), ("code", "code"), ("coach_number", "number"), ("phone", "phone"),
             ("email", "email"), ("invoice_start", "invoice_start")]


def build_me_files(drive: Drive) -> list[str]:
    """Each coach's <slug>.me Doc, from their row in the head coach's list of coaches. Returns slugs whose file changed.

    The coach's Claude and the invoice generator read it; the coach can't open the hub, so this is how their
    number, phone and email reach them. Changing a coach's details means changing their row, then rebuilding."""
    changed = []
    for c in drive.coaches(active_only=False):
        folder = drive.coach_dir(c["slug"])
        if not folder.is_dir():
            continue
        fm = "".join(f"{key}: {c.get(col, '')}\n" for key, col in ME_FIELDS)
        text = (f"Me\n\nGenerated from the head coach's list of coaches. Read only: ask the head coach to change "
                f"anything here.\n\n{fm}role: coach\n\nThe only per-coach details on an invoice are this coach's phone and "
                "email. Everything else comes from factory/business.\n")
        path = coach_me(folder)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(c["slug"])
    return changed


def build_client_lists(drive: Drive) -> list[str]:
    """Each coach's clients Sheet, from the head coach's main list. Returns slugs whose list changed.

    The coach never edits it: it changes when the head coach assigns, moves, or reactivates a client."""
    clients = read_table(drive.hub / "clients.csv")
    changed = []
    for slug in drive.all_coach_slugs():
        mine = [c for c in clients if c.get("coach") == slug and c.get("status") in ("active", "new")]  # filter per coach
        if write_generated(drive.coach_dir(slug) / "clients.csv", "My clients",
                           "Your clients, from the head coach's main list. It updates by itself when the head coach "
                           "assigns or moves a client. Read only.",
                           [("Clients", CLIENT_COLUMNS, mine)]):
            changed.append(slug)
    return changed


def unpaid_rows(books: Books, coach: str | None, as_of: str) -> list[dict]:
    """Open invoices with how long each has been unpaid, longest first. Invoices are due on receipt,
    so days unpaid count from the invoice date."""
    rows = [{"coach": inv["coach"], "invoice": inv.get("reference") or inv["number"], "date": inv["date"],
             "client_id": inv["client_id"], "client": inv.get("client", ""), "payer": inv.get("payer", ""),
             "amount": inv["amount"], "still_owed": fmt(inv["balance"]), "days_unpaid": days_between(inv["date"], as_of),
             "id": inv["number"]}
            for inv in books.open_invoices(coach)]
    return sorted(rows, key=lambda r: (-r["days_unpaid"], r["id"]))


def build_coach_views(drive: Drive, books: Books, as_of: str | None = None) -> list[str]:
    """Rebuild every coach's unpaid Sheet. Returns slugs whose unpaid Sheet changed.

    A coach sees one thing about money: which invoices are unpaid, and for how long (on the
    list = still owed; not on it = settled). No payment dates, amounts received, bank lines,
    overpayments or how a payment was matched.
    """
    as_of = as_of or today()
    changed = []
    for slug in drive.all_coach_slugs():
        rows = unpaid_rows(books, slug, as_of)                                  # the confidentiality filter
        cols = ["invoice", "date", "client_id", "client", "payer", "amount", "still_owed", "days_unpaid", "id"]
        total = sum((money(r["still_owed"]) for r in rows), ZERO)
        warn = "".join(f"\n⚠ {m}. The head coach has been told." for m in books.coach_problems.get(slug, []))
        if write_generated(drive.coach_dir(slug) / "unpaid.csv", "Unpaid",
                           f"Outstanding: {fmt(total)} across {len(rows)} invoice(s), longest unpaid first. Any of "
                           "your invoices not listed here is settled. If a client says they've already paid, ask for "
                           "proof of payment and pass it to the head coach." + warn
                           + "\nLists checked: " + ", ".join(sorted(books.lists_seen.get(slug, []))),
                           [("Unpaid invoices", cols, rows)]):
            changed.append(slug)
    return changed


def build_hub_views(drive: Drive, books: Books, as_of: str | None = None) -> None:
    as_of = as_of or today()
    efts = books.open_efts()
    eft_dates = {e["eft_id"]: e["date"] for e in books.ledger}

    def rows(state):
        return [{"eft_id": e["eft_id"], "received": e["date"], "amount": e["amount"], "remaining": fmt(e["remaining"]),
                 "days": days_between(e["date"], as_of), "description": e["description"]}
                for e in efts if e["state"] == state]

    unrec, unrev = rows("unreconciled"), rows("unreviewed")
    total = sum((money(r["remaining"]) for r in unrec), ZERO)
    cols = ["eft_id", "received", "amount", "remaining", "days", "description"]
    write_generated(drive.hub / "unreconciled.csv", "Unreconciled payments",
                    f"Head coach only. Live list: {len(unrec)} payment(s), {fmt(total)} of verified client money "
                    "not yet tied to an invoice. It carries over from recon to recon and shrinks as proofs of payment "
                    "come in.",
                    [("Client money, not yet matched (live list)", cols, unrec),
                     ("Not yet reviewed — client money or not?", cols, unrev),
                     ("Proofs of payment waiting for the POP recon", ["file", "state", "date", "amount", "payer"],
                      books.pops_waiting())])

    summary = []
    for slug in drive.all_coach_slugs():
        invs = [i for i in books.invoices.values() if i["coach"] == slug]
        open_ = books.open_invoices(slug)
        summary.append({
            "coach": slug,
            "invoices": len(invs),
            "invoiced": fmt(sum((money(i["amount"]) for i in invs), ZERO)),
            "collected": fmt(sum((money(a["amount"]) for a in books.allocations
                                  if a.get("coach") == slug and a["kind"] == "payment"), ZERO)),
            "written_off": fmt(sum((money(a["amount"]) for a in books.allocations
                                    if a.get("coach") == slug and a["kind"] == "write-off"), ZERO)),
            "open": len(open_),
            "outstanding": fmt(sum((i["balance"] for i in open_), ZERO)),
        })
    checks = [{"problem": m} for m in books.problems]
    write_generated(drive.hub / "summary.csv", "Summary",
                    f"All coaches. Head coach only. Unreconciled live list: {len(unrec)} payment(s), {fmt(total)}.",
                    [("By coach", ["coach", "invoices", "invoiced", "collected", "written_off", "open", "outstanding"],
                      summary),
                     ("Unpaid invoices — all coaches, longest unpaid first",
                      ["coach", "invoice", "date", "client_id", "client", "amount", "still_owed", "days_unpaid", "id"],
                      unpaid_rows(books, None, as_of)),
                     ("Updated invoices — re-issued by the coach with a new amount",
                      ["coach", "invoice", "client", "was", "now", "list"], books.updates),
                     ("Folder checks — things the system didn't make, or that changed", ["problem"], checks),
                     ("Overpayments — handle in your own accounting system", ["date", "eft_id", "coach", "client_id",
                                                                             "invoice", "amount"],
                      [{"date": eft_dates.get(a.get("eft_id"), a["date"]), "eft_id": a.get("eft_id", ""),
                        "coach": a["coach"], "client_id": a["client_id"], "invoice": a.get("invoice", ""),
                        "amount": a["amount"]} for a in books.overpayments()])])

