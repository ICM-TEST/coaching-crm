#!/usr/bin/env python3
"""The head coach's two recons — and only two — plus the two records that aren't recons.

  Recon 1, bank:  bank statements (read into hub/bank/lines/)  <->  the coaches' invoice lists
    recon.py --root <drive> bank [--month-end 2026-11] [--force] [--skip-balance-check]
  Recon 2, POP:   proofs of payment  <->  the unreconciled live list (nothing else)
    recon.py --root <drive> pops
  Either recon, after the head coach has decided every '?':
    recon.py --root <drive> push hub/recon/bank-2026-12-05.md

  Not a recon — a record of what the head coach agreed with a coach:
    recon.py --root <drive> write-off <invoice number> --reason "<reason>"

Overpayments: the invoice is paid and the excess is recorded as an overpayment, listed for the
head coach to handle in their own accounting system. This system keeps no client credit.

There is no other way to tie a payment to an invoice. Proposals never change anyone's
money; push refuses while any decision is still '?', and re-checks every row.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import itertools
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import (ALLOC_COLUMNS, LEDGER_COLUMNS, REVIEW_COLUMNS, Books, build_client_lists,  # noqa: E402
                       build_coach_views, build_hub_views, build_me_files, drive_index)
from crm.common import (ZERO, Drive, append_rows, fmt, iso_date, money, read_sheet, read_table,  # noqa: E402
                        set_sheet_meta, today, write_sheet)
from runs import gate  # noqa: E402

PROPOSAL_COLUMNS = ["line", "eft_id", "eft_date", "eft_amount", "description", "coach", "client_id", "invoice",
                    "amount", "kind", "confidence", "decision", "note"]
POP_PROPOSAL_COLUMNS = ["line", "pop", "pop_date", "pop_amount", "payer", "eft_id", "eft_date", "description", "coach",
                        "client_id", "invoice", "amount", "kind", "confidence", "decision", "note"]
DECISIONS = {"bank": {"accept", "unreconciled", "non-client", "hold"}, "pop": {"accept", "hold"}}
# Proposal notes are for the head coach and can name other coaches' clients (the
# options lists). Allocations reach coach folders, so they carry only these fixed notes.
SAFE_NOTES = {"overpayment": "overpaid: head coach handles the excess", "write-off": "write-off confirmed"}


# ---------- reading the bank statements ----------
# Statements go in hub/bank/ exactly as the bank gives them, CSV or PDF, from any bank. The head coach's Claude reads
# each new one into a Sheet of the same name in hub/bank/lines/, in one layout for every bank (LINE_COLUMNS), and the
# recon reads only those. Every statement is checked against its running balance, so a misread or missing line stops
# the recon before anything is recorded.

LINE_COLUMNS = ["date", "description", "amount", "balance"]
PLAIN_NUMBER = re.compile(r"-?\d+(\.\d{1,2})?")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class StatementProblem(Exception):
    pass


def statements(drive: Drive) -> tuple[list[str], dict[str, Path]]:
    """Every statement on the drive, by file name, and the lines already read from each, by statement file name."""
    bank = drive.hub / "bank"
    local = {p.name for p in bank.iterdir() if p.is_file() and not p.name.startswith(".")} if bank.is_dir() else set()
    listed = {k[len("hub/bank/"):] for k in drive_index(drive.root) if k.startswith("hub/bank/") and k.count("/") == 2}
    lines_dir = bank / "lines"
    lines = {p.name[:-4]: p for p in sorted(lines_dir.glob("*.csv"))} if lines_dir.is_dir() else {}
    return sorted((local | listed) - {"README.txt"}), lines


def _is_date(value: str) -> bool:
    try:
        return bool(ISO_DATE.fullmatch(value)) and bool(dt.date.fromisoformat(value))
    except ValueError:
        return False


def check_lines(name: str, rows: list[dict]) -> list[str]:
    """Problems with one statement's lines: a missing column, or a value not in the one layout."""
    where = f"hub/bank/lines/{name}"
    missing = [c for c in LINE_COLUMNS if rows and c not in rows[0]]
    if missing:
        return [f"{where}: no column {', '.join(missing)} (it needs {', '.join(LINE_COLUMNS)})"]
    problems = []
    for n, r in enumerate(rows, 1):
        d, a, b = ((r.get(c) or "").strip() for c in ("date", "amount", "balance"))
        if not _is_date(d):
            problems.append(f"{where} line {n}: date '{d}' isn't YYYY-MM-DD")
        if not PLAIN_NUMBER.fullmatch(a):
            problems.append(f"{where} line {n}: amount '{a}' isn't a plain number (money in 1400.00, money out -85.00)")
        if b and not PLAIN_NUMBER.fullmatch(b):
            problems.append(f"{where} line {n}: balance '{b}' isn't a plain number")
    return problems


def balance_break(rows: list[dict]) -> int | None:
    """None if every balance follows from the line before it (banks list oldest or newest first), else the first
    line, counted as written, where it doesn't."""
    def first_break(seq):
        return next((i for i in range(1, len(seq))
                     if money(seq[i]["balance"]) != money(seq[i - 1]["balance"]) + money(seq[i]["amount"])), None)
    forward = first_break(rows)
    return None if forward is None or first_break(rows[::-1]) is None else forward + 1


def import_bank(drive: Drive, check_balances: bool = True) -> tuple[int, list[str], list[str]]:
    """New money-in lines into the ledger. Returns (lines added, what was read from each new statement, warnings)."""
    names, read = statements(drive)
    unread = [n for n in names if n not in read]
    if unread:
        raise StatementProblem("these statements haven't been read into hub/bank/lines/ yet: " + ", ".join(unread)
                               + ". Read each one first (roles/head-coach/skills/recon.md, Read new statements).")
    tables = {name: read_table(path) for name, path in read.items()}
    problems = [p for name, rows in tables.items() for p in check_lines(name, rows)]
    check = {}
    for name, rows in tables.items():
        if problems:
            break
        if rows and all((r.get("balance") or "").strip() for r in rows):
            line = balance_break(rows)
            if line and check_balances:
                problems.append(f"hub/bank/lines/{name} line {line}: the balance doesn't follow from the line before. "
                                f"A line is misread or missing: read that part of {name} again.")
            check[name] = "balance check SKIPPED" if line else "every balance checked"
        else:
            check[name] = "no running balance: compare the money-in total with the statement"
    if problems:
        raise StatementProblem("\n  ".join(problems))

    ledger = read_table(drive.hub / "eft-ledger.csv")
    known = {e["eft_id"] for e in ledger}
    sources = {e.get("source", "") for e in ledger}
    same_day = defaultdict(list)                           # (date, amount) -> payments, to spot one read twice
    for e in ledger:
        same_day[(iso_date(e["date"]), fmt(money(e["amount"])))].append(e)
    new_rows, report, warnings = [], [], []
    for name, rows in tables.items():
        seen, added = Counter(), 0
        here = {(r["date"].strip(), fmt(money(r["amount"])), " ".join(r["description"].split())) for r in rows}
        for r in rows:
            amount = money(r["amount"])
            if amount <= ZERO:
                continue                                    # money out: not client money
            date, desc = r["date"].strip(), " ".join(r["description"].split())
            balance = fmt(money(r["balance"])) if (r.get("balance") or "").strip() else ""
            key = f"{date}|{fmt(amount)}|{desc}|{balance}"
            seen[key] += 1                                  # the same line twice in one statement = two payments
            eft_id = "E" + hashlib.sha1(f"{key}|{seen[key]}".encode()).hexdigest()[:10]
            if eft_id in known:
                continue                                    # overlapping statements: already in the ledger
            twin = next((e for e in same_day[(date, fmt(amount))] if e.get("source") != name
                         and (iso_date(e["date"]), fmt(money(e["amount"])), e["description"]) not in here), None)
            if twin:
                warnings.append(f"Possible double: {name} has {fmt(amount)} on {date} ('{desc}'), and {twin['source']} "
                                f"had the same amount that day ('{twin['description']}'). If it's the same payment, "
                                f"decide it non-client so it isn't counted twice.")
            row = {"eft_id": eft_id, "date": date, "amount": fmt(amount), "description": desc, "source": name}
            known.add(eft_id)
            same_day[(date, row["amount"])].append(row)
            new_rows.append(row)
            added += 1
        if added or name not in sources:
            ins = [money(r["amount"]) for r in rows if money(r["amount"]) > ZERO]
            outs = [money(r["amount"]) for r in rows if money(r["amount"]) < ZERO]
            dates = sorted(r["date"].strip() for r in rows)
            span = f"{dates[0]} to {dates[-1]}" if dates else "no lines"
            report.append(f"{name}: {len(rows)} lines, {span}, money in {fmt(sum(ins, ZERO))} ({len(ins)}), "
                          f"money out {fmt(sum(outs, ZERO))} ({len(outs)}); {check[name]}")
    append_rows(drive.hub / "eft-ledger.csv", LEDGER_COLUMNS, new_rows)
    return len(new_rows), report, warnings


# ---------- recon 1: the bank statements against the invoice lists ----------

def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def _tokens(*names: str) -> set[str]:
    return {t for n in names for t in re.findall(r"[A-Z]+", (n or "").upper()) if len(t) >= 3}


def _refs(inv: dict) -> set[str]:
    """What a client might type for this invoice: its id, its reference (2026-03-490 → 202603490), and the
    reference without the year (03490), because clients often leave the year off."""
    ref = _norm(inv.get("reference", ""))
    short = ref[4:] if re.match(r"(19|20)\d\d", ref) else ""
    return {r for r in (_norm(inv["number"]), ref, short) if len(r) >= 4}


class Matcher:
    def __init__(self, books: Books):
        self.books = books
        self.bal = {n: books.balance(n) for n in books.invoices}     # working balances inside this proposal
        self.rows: list[dict] = []

    def _open(self):
        return sorted((i for n, i in self.books.invoices.items() if self.bal[n] > ZERO),
                      key=lambda i: (i["date"], i["number"]))

    def _row(self, eft, inv=None, amount=ZERO, kind="", confidence="", decision="accept", note="", coach="",
             client_id=""):
        row = {"eft_id": eft["eft_id"] if eft else "", "eft_date": eft["date"] if eft else "",
               "eft_amount": eft["amount"] if eft else "", "description": eft["description"] if eft else "",
               "coach": inv["coach"] if inv else coach, "client_id": inv["client_id"] if inv else client_id,
               "invoice": inv["number"] if inv else "", "amount": fmt(amount) if amount else "",
               "kind": kind, "confidence": confidence, "decision": decision, "note": note}
        self.rows.append(row)
        if inv and decision == "accept" and kind == "payment":
            self.bal[inv["number"]] -= amount

    def _pay_in_order(self, eft, invoices, amount, confidence, note=""):
        remaining = amount
        for inv in invoices:
            if remaining <= ZERO:
                break
            part = min(remaining, self.bal[inv["number"]])
            if part > ZERO:
                self._row(eft, inv, part, "payment", confidence, note=note)
                remaining -= part
        if remaining > ZERO:
            last = invoices[-1]
            self._row(eft, last, remaining, "overpayment", confidence,
                      note="overpaid: head coach handles the excess outside this system")

    def match(self, eft) -> None:
        """Unreviewed EFTs always get a row; '?' when the head coach must decide.
        EFTs already on the live list get a row only for a confident new match."""
        live = eft["state"] == "unreconciled"
        amount, desc = eft["remaining"], eft["description"]
        norm, words = _norm(desc), set(re.findall(r"[A-Z]+", desc.upper()))
        open_ = self._open()

        # A. invoice number or payment reference in the bank description. Printed numbers ("2026 #490") can
        #    repeat across coaches, so a reference that fits more than one client is never paid automatically.
        refs = [i for i in open_ if any(r in norm for r in _refs(i))]
        if refs and len({(i["coach"], i["client_id"]) for i in refs}) > 1:
            if live:
                return
            options = " / ".join(f"{i['number']} ({i['coach']}, {i.get('client', '')}, {fmt(self.bal[i['number']])})"
                                 for i in refs[:6])
            return self._row(eft, None, amount, "payment", "reference fits several coaches", "?", note="options: " + options)
        if refs:
            return self._pay_in_order(eft, refs, amount, "reference")
        paid_refs = [i for i in self.books.invoices.values() if any(r in norm for r in _refs(i))]
        if paid_refs and not live:
            inv = paid_refs[0]
            return self._row(eft, inv, amount, "overpayment", "reference to a paid invoice", "?",
                             note=f"{inv['number']} is already paid: accept as an overpayment, or unreconciled?")

        # B. client or payer name in the bank description
        cands = [i for i in open_ if _tokens(i.get("client", ""), i.get("payer", "")) & words]
        if cands:
            exact = [i for i in cands if self.bal[i["number"]] == amount]
            if len(exact) == 1:
                return self._row(eft, exact[0], amount, "payment", "name + amount")
            clients = defaultdict(list)
            for i in cands:
                clients[(i["coach"], i["client_id"])].append(i)
            for invs in clients.values():
                if len(invs) > 1 and sum((self.bal[i["number"]] for i in invs), ZERO) == amount:
                    return self._pay_in_order(eft, invs, amount, "name + amount (all open invoices)")
            fits = [c for k in (2, 3) for c in itertools.combinations(cands, k)
                    if sum((self.bal[i["number"]] for i in c), ZERO) == amount]
            if len(fits) == 1:
                return self._pay_in_order(eft, list(fits[0]), amount, "name + amount (split)",
                                          note="one payment across invoices")
            if live:
                return
            if len(clients) == 1:
                invs = next(iter(clients.values()))
                owed = sum((self.bal[i["number"]] for i in invs), ZERO)
                if amount > owed:
                    return self._pay_in_order(eft, invs, amount, "name, overpaid")
                return self._row(eft, invs[0], amount, "payment", "name, part-payment", "?",
                                 note=f"pays {fmt(amount)} of {fmt(owed)} owed — accept as part-payment?")
            options = " / ".join(f"{i['number']} ({i['coach']}, {i.get('client', '')}, {fmt(self.bal[i['number']])})"
                                 for i in cands[:6])
            return self._row(eft, None, amount, "payment", "name, several possible", "?", note="options: " + options)
        if live:
            return

        # C. amount only
        same = [i for i in open_ if self.bal[i["number"]] == amount]
        if len(same) == 1:
            return self._row(eft, same[0], amount, "payment", "amount only", "?",
                             note="only open invoice with this amount — accept, unreconciled, or non-client?")
        if same:
            options = " / ".join(f"{i['number']} ({i['coach']}, {i.get('client', '')})" for i in same[:6])
            return self._row(eft, None, amount, "payment", "amount only, several", "?", note="options: " + options)

        # D. nothing fits: the head coach says whether it's client money at all
        self._row(eft, None, amount, "payment", "no match", "?",
                  note="client money → unreconciled (live list) · not client money → non-client · or pick an invoice")


def bank(root, month_end: str | None, force: bool, check_balances: bool = True) -> int:
    drive = Drive(root)
    if month_end:
        done, missing = gate(drive, month_end)
        if missing and not force:
            print(f"GATE: not complete — {month_end} invoicing: {len(done)} of {len(done) + len(missing)} done.")
            print("Not done: " + ", ".join(c["name"] for c in missing))
            return 3
    try:
        added, read, warnings = import_bank(drive, check_balances)
    except StatementProblem as e:
        print(f"Refused: {e}")
        return 4
    books = Books(drive)
    m = Matcher(books)
    efts = books.open_efts()
    for eft in efts:
        m.match(eft)
    for n, row in enumerate(m.rows, 1):
        row["line"] = n

    path = new_proposal_path(drive, "bank")
    first_rows, seen_efts = [], set()                 # count each EFT once, however many invoices it pays
    for r in m.rows:
        if not r["eft_id"] or r["eft_id"] not in seen_efts:
            first_rows.append(r)
            seen_efts.add(r["eft_id"])
    by_conf = Counter(r["confidence"] for r in first_rows)
    undecided = sum(1 for r in m.rows if r["decision"] == "?")
    live = [e for e in efts if e["state"] == "unreconciled"]
    gate_note = ""
    if month_end:
        done, missing = gate(drive, month_end)
        gate_note = (f"Month-end {month_end}: "
                     f"{'all coaches done' if not missing else 'RUN ANYWAY — not done: ' + ', '.join(c['name'] for c in missing)}\n\n")
    summary = (f"New bank lines: {added} · New payments to place: {len(efts) - len(live)} · "
               f"Live unreconciled list checked: {len(live)} · Rows: {len(m.rows)}\n\n"
               + "".join(f"- {conf or 'other'}: {cnt}\n" for conf, cnt in sorted(by_conf.items()))
               + f"\nDecisions needed: {undecided} (rows with ?)\n"
               + (f"\nProofs of payment waiting for the POP recon: {len(books.pops_waiting())}\n" if books.pops_waiting() else ""))
    read_note = ("Read from new statements:\n" + "".join(f"- {r}\n" for r in read) + "\n") if read else ""
    problems = "".join(f"⚠ {p}\n" for p in warnings + books.problems)
    notes = (gate_note + read_note + summary + problems).splitlines() + [
        "Pick each decision: accept (the invoice shown, or one you choose by changing coach/client_id/invoice/amount) · "
        "unreconciled (client money, can't place it yet: live list) · non-client (not client money) · hold (next time)."]
    write_sheet(path, PROPOSAL_COLUMNS, m.rows, title=f"Bank recon {path.stem}", notes=[n for n in notes if n.strip()],
                meta={"type": "bank", "status": "proposed", "created": today(), "month_end": month_end or "",
                      "dropdown": "decision=?|" + "|".join(sorted(DECISIONS["bank"]))})
    print(f"Proposal: {path.relative_to(drive.root)}")
    print(read_note + summary + problems)
    return 0


# ---------- writing ----------

class Ledger:
    """Validates and stages money facts against current books, then writes them in one go."""

    def __init__(self, drive: Drive, recon: str):
        self.drive, self.recon = drive, recon
        self.books = Books(drive)
        self.eft_left = {e["eft_id"]: self.books.remaining(e) for e in self.books.ledger}
        self.bal = {n: self.books.balance(n) for n in self.books.invoices}
        self.allocs: list[dict] = []
        self.reviews: dict[str, str] = {}
        self.problems: list[str] = []

    def verdict(self, eft_id: str, verdict: str, where: str) -> None:
        if eft_id not in self.eft_left:
            self.problems.append(f"{where}: no EFT {eft_id} in the ledger")
            return
        if verdict == "non-client" and self.eft_left[eft_id] < money(self.books.eft(eft_id)["amount"]):
            self.problems.append(f"{where}: EFT {eft_id} already paid an invoice, so it can't be non-client")
            return
        if self.reviews.get(eft_id, verdict) != verdict:
            self.problems.append(f"{where}: EFT {eft_id} given two different verdicts")
            return
        if self.books.verdicts.get(eft_id) != verdict:
            self.reviews[eft_id] = verdict

    def alloc(self, where: str, kind: str, amount: Decimal, coach: str, client_id: str = "", invoice: str = "",
              eft_id: str = "", note: str = "", recon: str = "") -> None:
        if amount <= ZERO:
            return self.problems.append(f"{where}: amount must be above zero")
        if coach not in self.drive.all_coach_slugs():
            return self.problems.append(f"{where}: unknown coach '{coach}'")
        if kind == "overpayment" and invoice:
            inv = self.books.invoices.get(invoice)
            if not inv or inv["coach"] != coach or inv["client_id"] != client_id:      # never cross coaches
                return self.problems.append(f"{where}: overpayment on '{invoice}' doesn't match {coach}/{client_id}")
        if kind in ("payment", "write-off"):
            inv = self.books.invoices.get(invoice)
            if not inv:
                return self.problems.append(f"{where}: invoice '{invoice}' not found")
            if inv["coach"] != coach or inv["client_id"] != client_id:            # never cross coaches
                return self.problems.append(f"{where}: {invoice} belongs to {inv['coach']}/{inv['client_id']}, "
                                            f"not {coach}/{client_id}")
            if amount > self.bal[invoice]:
                return self.problems.append(f"{where}: {fmt(amount)} is more than {invoice}'s balance {fmt(self.bal[invoice])}")
            self.bal[invoice] -= amount
        if kind in ("payment", "overpayment"):
            if self.books.verdicts.get(eft_id) == "non-client" or self.reviews.get(eft_id) == "non-client":
                return self.problems.append(f"{where}: EFT {eft_id} is marked non-client")
            if amount > self.eft_left.get(eft_id, ZERO):
                return self.problems.append(f"{where}: EFT {eft_id} doesn't have {fmt(amount)} left")
            self.eft_left[eft_id] -= amount
        if kind not in ("payment", "overpayment", "write-off"):
            return self.problems.append(f"{where}: kind '{kind}' can't be recorded")
        self.allocs.append({"eft_id": eft_id, "coach": coach, "client_id": client_id, "invoice": invoice,
                            "amount": fmt(amount), "kind": kind, "note": note or SAFE_NOTES.get(kind, ""),
                            "recon": recon or self.recon})

    def commit(self) -> int:
        if self.problems:
            print("Refused — nothing written:")
            for p in self.problems:
                print("  " + p)
            return 1
        start = len(self.books.allocations) + 1
        self.books.archive_new()                # the head coach's copy of newly seen sealed invoices
        append_rows(self.drive.hub / "allocations.csv", ALLOC_COLUMNS,
                    [dict(a, id=f"A{start + i:06d}", date=today()) for i, a in enumerate(self.allocs)])
        append_rows(self.drive.hub / "eft-reviews.csv", REVIEW_COLUMNS,
                    [{"eft_id": e, "date": today(), "verdict": v, "recon": self.recon} for e, v in self.reviews.items()])
        books = Books(self.drive)
        build_me_files(self.drive)              # so a coach's details and client list can never lag the head coach's lists
        build_client_lists(self.drive)
        changed = build_coach_views(self.drive, books)
        build_hub_views(self.drive, books)
        live = [e for e in books.open_efts() if e["state"] == "unreconciled"]
        print(f"Recorded {len(self.allocs)} allocation(s), {len(self.reviews)} verdict(s).")
        print("Unpaid list changed for: " + (", ".join(changed) if changed else "nobody"))
        print(f"Unreconciled live list: {len(live)} payment(s), "
              f"{fmt(sum((e['remaining'] for e in live), ZERO))}")
        return 0


def new_proposal_path(drive: Drive, kind: str) -> Path:
    path, k = drive.hub / "recon" / f"{kind}-{today()}.csv", 2
    while path.exists():
        path, k = drive.hub / "recon" / f"{kind}-{today()}-{k}.csv", k + 1
    return path


def push(root, proposal: str) -> int:
    drive = Drive(root)
    path = Path(proposal)
    path = path if path.is_absolute() else drive.root / path
    meta, rows = read_sheet(path)
    kind_of = meta.get("type")
    if meta.get("status") != "proposed" or kind_of not in DECISIONS:
        print(f"Refused: {path.name} is not an open bank or POP proposal (type '{kind_of}', status '{meta.get('status')}').")
        return 2
    allowed = DECISIONS[kind_of]
    led = Ledger(drive, path.stem)
    undecided = [r["line"] for r in rows if r.get("decision") not in allowed]
    if undecided:
        led.problems.append(f"undecided lines (allowed: {', '.join(sorted(allowed))}): " + ", ".join(undecided))
    pops_in_use = {}
    for r in rows:
        d, where, eft_id = r.get("decision"), f"line {r['line']}", r.get("eft_id", "")
        if d not in allowed or d == "hold":
            continue
        if kind_of == "pop":
            # The POP recon may only reconcile against the live list: verified client money, still unplaced.
            if led.books.verdicts.get(eft_id) != "client":
                led.problems.append(f"{where}: EFT {eft_id} isn't on the unreconciled list — run the bank recon first")
                continue
            pop = r.get("pop", "")
            if pop in led.books.pops_used() or pops_in_use.get(pop, eft_id) != eft_id:
                led.problems.append(f"{where}: POP {pop} is already used")
                continue
            pops_in_use[pop] = eft_id
            if led.books.pop_coach(pop) and led.books.pop_coach(pop) != r.get("coach"):
                led.problems.append(f"{where}: POP {pop} was uploaded by {led.books.pop_coach(pop)}, not {r.get('coach')}")
                continue
            led.alloc(where, r.get("kind", ""), money(r.get("amount")), r.get("coach", ""), r.get("client_id", ""),
                      r.get("invoice", ""), eft_id, note="matched with proof of payment" if r.get("kind") == "payment" else "",
                      recon=f"pop:{pop}")
            continue
        if d in ("unreconciled", "non-client"):
            if not eft_id:
                led.problems.append(f"{where}: '{d}' needs an EFT")
                continue
            led.verdict(eft_id, "client" if d == "unreconciled" else "non-client", where)
            continue
        if eft_id:
            led.verdict(eft_id, "client", where)          # accepting a match says it's client money
        led.alloc(where, r.get("kind", ""), money(r.get("amount")), r.get("coach", ""), r.get("client_id", ""),
                  r.get("invoice", ""), eft_id)
    code = led.commit()
    if code == 0:
        set_sheet_meta(path, "status", "pushed")
        set_sheet_meta(path, "pushed", today())
    return code


# ---------- recon 2: proofs of payment against the unreconciled live list ----------

def pops(root) -> int:
    drive = Drive(root)
    books = Books(drive)
    live = [e for e in books.open_efts() if e["state"] == "unreconciled"]
    eft_left = {e["eft_id"]: e["remaining"] for e in live}
    bal = {n: books.balance(n) for n in books.invoices}
    used = books.pops_used()
    waiting = [p for p in books.pop_register() if p["file"] not in used]
    unread = [p for p in books.pops_waiting() if p["state"] == "not read yet"]
    if not waiting:
        print("No proofs of payment in the register waiting for a match. Nothing to propose."
              + (f"\n⚠ {len(unread)} POP file(s) aren't in the register yet: read them first." if unread else ""))
        return 0
    rows = []

    def row(p, eft=None, inv=None, amount=ZERO, kind="payment", confidence="", decision="accept", note="",
            coach="", client_id=""):
        rows.append({"pop": p["file"], "pop_date": p["date"], "pop_amount": p["amount"], "payer": p.get("payer", ""),
                     "eft_id": eft["eft_id"] if eft else "", "eft_date": eft["date"] if eft else "",
                     "description": eft["description"] if eft else "",
                     "coach": inv["coach"] if inv else coach, "client_id": inv["client_id"] if inv else client_id,
                     "invoice": inv["number"] if inv else "", "amount": fmt(amount) if amount else "",
                     "kind": kind, "confidence": confidence, "decision": decision, "note": note})
        if inv and decision == "accept" and kind == "payment":
            bal[inv["number"]] -= amount

    for p in waiting:
        amount, names = money(p["amount"]), _tokens(p.get("payer", ""), p.get("client", ""))
        # 1. the payment on the live list: same amount, within a week of the POP's date
        efts = [e for e in live if eft_left[e["eft_id"]] == amount
                and abs((dt.date.fromisoformat(e["date"]) - dt.date.fromisoformat(p["date"])).days) <= 7]
        if len(efts) > 1:
            named = [e for e in efts if names & _tokens(e["description"])]
            efts = named or sorted(efts, key=lambda e: abs((dt.date.fromisoformat(e["date"])
                                                            - dt.date.fromisoformat(p["date"])).days))[:1]
        if not efts:
            row(p, confidence="no payment on the live list", decision="hold",
                note="not cleared yet, another account, or the bank recon hasn't run since it arrived")
            continue
        eft = efts[0]
        # 2. the invoice: the one the coach named (in the register or the file name), else by name/reference.
        #    A POP a coach uploaded can only be for that coach's invoices.
        coach = books.pop_coach(p["file"])
        open_ = [i for n, i in books.invoices.items() if bal[n] > ZERO and (not coach or i["coach"] == coach)]
        named_inv = books.invoices.get(p.get("invoice", "")) or next(
            (i for i in open_ if any(r in _norm(Path(p["file"]).stem) for r in _refs(i))), None)
        if named_inv and bal[named_inv["number"]] > ZERO:
            cands = [named_inv]
        else:
            ref = _norm(p.get("reference", ""))
            cands = [i for i in open_ if (ref and any(r in ref for r in _refs(i)))
                     or names & _tokens(i.get("client", ""), i.get("payer", ""))]
        clients = {(i["coach"], i["client_id"]) for i in cands}
        if len(clients) == 1:
            invs = sorted(cands, key=lambda i: (i["date"], i["number"]))
            left, conf = amount, "POP + invoice named" if named_inv else "POP + name"
            for inv in invs:
                part = min(left, bal[inv["number"]])
                if part > ZERO:
                    row(p, eft, inv, part, "payment", conf)
                    left -= part
            if left > ZERO:
                row(p, eft, invs[-1], left, "overpayment", conf,
                    note="overpaid: head coach handles the excess outside this system")
            eft_left[eft["eft_id"]] = ZERO
            continue
        options = " / ".join(f"{i['number']} ({i['coach']}, {i.get('client', '')}, {fmt(bal[i['number']])})" for i in cands[:6])
        row(p, eft, None, amount, "payment", "POP, invoice unclear", "?",
            note=("options: " + options) if options else "no open invoice fits — set coach/client_id/invoice")

    for n, r in enumerate(rows, 1):
        r["line"] = n
    path = new_proposal_path(drive, "pop")
    undecided = sum(1 for r in rows if r["decision"] == "?")
    matched = len({r["pop"] for r in rows if r["decision"] == "accept"})
    summary = (f"POPs in the register, not yet used: {len(waiting)} · Matched to the live list: {matched} · "
               f"No payment found yet: {sum(1 for r in rows if r['decision'] == 'hold')}\n\n"
               f"Decisions needed: {undecided} (rows with ?)\n"
               + (f"\n⚠ {len(unread)} POP file(s) aren't in the register yet: read them first.\n" if unread else ""))
    notes = summary.splitlines() + [
        "Proofs of payment against the unreconciled live list only. Pick each decision: accept (change "
        "coach/client_id/invoice/amount first if needed) or hold (the POP waits for a later POP recon)."]
    write_sheet(path, POP_PROPOSAL_COLUMNS, rows, title=f"POP recon {path.stem}", notes=[n for n in notes if n.strip()],
                meta={"type": "pop", "status": "proposed", "created": today(),
                      "dropdown": "decision=?|" + "|".join(sorted(DECISIONS["pop"]))})
    print(f"Proposal: {path.relative_to(drive.root)}")
    print(summary)
    return 0


# ---------- not a recon: a record of what the head coach agreed with a coach ----------

def write_off(root, invoice: str, amount: str | None, reason: str) -> int:
    drive = Drive(root)
    led = Ledger(drive, "direct")
    inv = led.books.invoices.get(invoice)
    if not inv:
        print(f"Refused: invoice {invoice} not found")
        return 1
    led.alloc("write-off", "write-off", money(amount) if amount else led.bal[invoice], inv["coach"],
              inv["client_id"], invoice, note=f"write-off confirmed: {reason}" if reason else "")
    return led.commit()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bank", help="recon 1: bank statements against the invoice lists")
    b.add_argument("--month-end"); b.add_argument("--force", action="store_true")
    b.add_argument("--skip-balance-check", action="store_true", help="only when the head coach has checked the totals")
    sub.add_parser("pops", help="recon 2: proofs of payment against the unreconciled list")
    q = sub.add_parser("push"); q.add_argument("proposal")
    w = sub.add_parser("write-off"); w.add_argument("invoice"); w.add_argument("--amount")
    w.add_argument("--reason", default="")
    a = ap.parse_args()
    sys.exit({
        "bank": lambda: bank(a.root, a.month_end, a.force, not a.skip_balance_check),
        "pops": lambda: pops(a.root),
        "push": lambda: push(a.root, a.proposal),
        "write-off": lambda: write_off(a.root, a.invoice, a.amount, a.reason),
    }[a.cmd]())


if __name__ == "__main__":
    main()
