#!/usr/bin/env python3
"""The invoice generator: a coach's two outputs, made in one step.

  issue.py --root <drive> --coach-dir coach-<slug> --period 2026-11 --drafts drafts.json --dry-run
  issue.py --root <drive> --coach-dir coach-<slug> --period 2026-11 --drafts drafts.json

Run by the coach's Claude. Needs only the coach's folder and factory/. Rules: factory/invoice-rules.md.
Every invoice is the business's own layout; only the coach's phone and email change from coach to coach.
The drafts file is the approved drafts, kept outside the drive (the coach produces nothing else):

  {"invoices": [{"client_id": "C0001", "payer": "P Radebe",
                 "lines": [{"code": "SQD60", "month": "2026-11", "qty": 4},
                           {"code": "PVT", "month": "2026-10", "qty": 2}]}]}

To update an invoice a client hasn't paid (lessons cancelled, say), on its own and with the invoice's own --period:

  {"updates": [{"invoice": "2026-03-490", "lines": [{"code": "PVT", "month": "2026-10", "qty": 2}]}]}

It keeps its number and date. A new PDF and a new sealed list carry the new amount, which recon then uses; the original
list and PDF stay as they are. For a whole invoice cancelled: {"invoice": "2026-03-490", "cancel": true, "lines": []}.
An invoice already paid is refused: the coach adjusts their future invoices instead.

--dry-run shows exactly what would be issued (numbers, lines, totals) and writes nothing.
Otherwise it writes the PDFs to invoices/<period>/ first, then the run's list to invoice-lists/ last.

Through the Google Drive connector (from anywhere, a phone included), --root is a working copy in Claude's own
workspace, not the drive itself:
  issue.py --coach-dir coach-<slug> --needs        which drive files to download into the working copy
  … run as above against the working copy …        it ends by listing what to upload, in order
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import GENERATOR, LIST_COLUMNS, file_hash, invoice_lists, list_seal  # noqa: E402
from crm.common import ZERO, coach_me, fmt, frontmatter, is_placeholder, money, read_sections, read_table, write_sheet  # noqa: E402


CURRENCY = {"symbol": "R"}                  # Rand unless factory/business sets currency_symbol; set when the run is planned


def money_text(amount: Decimal) -> str:
    """1,440.00 with the business's currency symbol in front, the way its invoices write money."""
    return f"{'-' if amount < 0 else ''}{CURRENCY['symbol']}{abs(amount):,.2f}"


def nice_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d:%b %Y}"


def printed_number(fmt_: str, year: int, coach_no: str, seq: int) -> str:
    """The number on the invoice, and the payment reference: year - coach number - invoice number, e.g. 2026-03-490."""
    return (fmt_ or "{year}-{coach}-{seq}").format(year=year, coach=coach_no, seq=seq)


# ---------- building the run ----------

class Refused(Exception):
    pass


def _paid_so_far(folder: Path, number: str, list_files: set) -> Decimal | None:
    """What the coach's unpaid Sheet says is paid on an invoice; None if it's settled. A coach can't see the books, and
    an invoice no recon has checked yet isn't on the Sheet either, so `Lists checked` tells the two apart."""
    path = folder / "unpaid.csv"
    if not path.exists():
        raise Refused(f"{folder.name}/unpaid isn't in the working copy. Download it first: an update needs it to see "
                      "whether the invoice has been paid.")
    rows = read_sections(path).get("Unpaid invoices", [])
    row = next((r for r in rows if r.get("id") == number), None)
    if row:
        return money(row["amount"]) - money(row["still_owed"])
    m = re.search(r"^\"?# Lists checked: (.*?)\"?$", path.read_text(encoding="utf-8"), re.M)
    checked = {x.strip() for x in m.group(1).split(",")} if m else set()
    return None if list_files & checked else ZERO


def plan(root: Path, coach_dir: str, period: str, drafts: dict, issue_date: str | None, extra: bool) -> dict:
    folder, factory = root / coach_dir, root / "factory"
    me_doc = f"{coach_dir}/{coach_me(folder).name[:-4]}"
    me, biz = frontmatter(coach_me(folder)), frontmatter(factory / "business.txt")
    unset = [k for k, v in biz.items() if is_placeholder(v)]
    if unset:
        raise Refused("factory/business isn't finished: " + ", ".join(unset) + " still hold a <placeholder>. The head "
                      "coach fills each one in, or leaves it blank, before any invoice is issued.")
    CURRENCY["symbol"] = str(biz.get("currency_symbol", "R")).strip()     # Rand by default
    if me.get("role") != "coach" or not me.get("code"):
        raise Refused(f"{me_doc} isn't a coach's details Doc")
    coach_no = str(me.get("coach_number", "")).strip()
    if "{coach}" in (biz.get("invoice_number_format") or "{coach}") and not coach_no.isdigit():
        raise Refused(f"{me_doc} has no coach_number: every coach needs their own, e.g. 03")
    coach_no = coach_no.zfill(2)
    if not re.fullmatch(r"\d{4}-\d{2}", period):
        raise Refused(f"period must look like 2026-11, not '{period}'")
    code = me["code"]
    if not issue_date:
        day = str(biz.get("invoice_day", "")).strip()
        if not day.isdigit():
            raise Refused("invoice_day in factory/business isn't set: the day of the month invoices go out.")
        issue_date = f"{period}-{int(day):02d}"
    year = int(issue_date[:4])
    rates = {r["code"]: r for r in read_table(factory / "billable-work.csv")}
    lists = invoice_lists(folder)
    issued = {r["number"]: r for _, rows in lists for r in rows}
    clients = {r["client_id"]: {"name": r["client"], "phone": ""} for r in issued.values()}   # billed before
    clients.update({c["id"]: {"name": c["name"], "phone": c.get("phone", "")}
                    for c in read_table(folder / "clients.csv")})                            # current clients

    if not any(r.get("period") == period for r in read_table(factory / "invoicing-runs.csv")):
        raise Refused(f"the head coach hasn't opened {period} invoicing yet")
    if not (folder / "invoices" / period).is_dir():
        raise Refused(f"{coach_dir}/invoices/{period}/ doesn't exist. The head coach's Claude makes it when it opens the "
                      "run; ask the head coach. Never create it yourself.")
    if drafts.get("credit_notes"):
        raise Refused("This system has no credit notes. Update the invoice while it's unpaid; once it's paid, adjust "
                      "the client's future invoices.")
    updates = drafts.get("updates", [])
    if updates and drafts.get("invoices"):
        raise Refused("Update issued invoices on their own, not in the same step as new invoices.")
    same_period = [m["file"] for m, _ in lists if m["period"] == period]
    if same_period and not extra and not updates:
        raise Refused(f"{period} is already issued ({', '.join(same_period)}). For something genuinely missed, "
                      "issue an extra list with --extra.")
    list_name = f"{period}.csv" if not same_period else f"{period}-{len(same_period) + 1}.csv"

    # Each coach has their own running sequence, carried on from their old app (invoice_start in their .me Doc).
    # The printed number carries the coach's own number (2026-03-490), so it's unique across coaches and works
    # as the payment reference. The internal id carries the coach's code as well, as a second guard.
    seqs = [int(n.rsplit("-", 1)[-1]) for n in issued if n.startswith(f"{code}-") and n.rsplit("-", 1)[-1].isdigit()]
    next_seq = max(seqs, default=int(me.get("invoice_start") or 1) - 1) + 1

    def take_number() -> tuple[str, str]:
        nonlocal next_seq
        seq, next_seq = next_seq, next_seq + 1
        return f"{code}-{year}-{seq:04d}", printed_number(biz.get("invoice_number_format", ""), year, coach_no, seq)

    problems, docs, seen = [], [], set()

    def build_lines(label: str, wanted: list) -> list:
        lines = []
        for j, ln in enumerate(wanted, 1):
            rate = rates.get(ln.get("code", ""))
            if not rate:
                problems.append(f"{label} line {j}: '{ln.get('code')}' isn't in factory/billable-work")
                continue
            qty = Decimal(str(ln.get("qty", 1)))
            if qty <= 0:
                problems.append(f"{label} line {j}: quantity must be above zero")
                continue
            month = ln.get("month", period)
            # Group sessions are billed in advance (up to next month); everything else for the month past.
            advance = rate.get("billed", "").strip().lower() == "in advance"
            y_, m_ = int(period[:4]), int(period[5:])
            latest = f"{y_ + m_ // 12}-{m_ % 12 + 1:02d}" if advance else period
            if not re.fullmatch(r"\d{4}-\d{2}", month) or month > latest:
                why = "billed in advance, at most a month ahead" if advance else "billed for the month past"
                problems.append(f"{label} line {j}: month '{month}' must be YYYY-MM and not after {latest} "
                                f"({rate['name']} is {why})")
                continue
            item = f"{rate['name']} - {calendar.month_name[int(month[5:])]}"
            lines.append({"item": item, "month": month, "qty": qty, "price": money(rate["rate"]),
                          "amount": money(rate["rate"]) * qty})
        return sorted(lines, key=lambda l: (l["month"], l["item"]), reverse=True)

    for i, inv in enumerate(drafts.get("invoices", []), 1):
        cid = inv.get("client_id", "")
        if cid not in clients:
            problems.append(f"invoice {i}: {cid or '(no client)'} isn't on your client list. Ask the head coach to add them.")
            continue
        if cid in seen:
            problems.append(f"invoice {i}: {cid} has two invoices in this run. One invoice per client per run.")
        seen.add(cid)
        lines = build_lines(f"invoice {i}", inv.get("lines", []))
        if not lines:
            problems.append(f"invoice {i}: no billable lines")
            continue
        number, shown = take_number()
        docs.append({"kind": "invoice", "number": number, "shown": shown, "client_id": cid,
                     "client": clients[cid]["name"], "phone": clients[cid]["phone"], "payer": inv.get("payer", "").strip(),
                     "lines": lines, "total": sum((l["amount"] for l in lines), ZERO)})

    for i, up in enumerate(updates, 1):
        ref = up.get("invoice", "")
        target = issued.get(ref) or next((r for r in issued.values() if r.get("reference") == ref), None)
        if not target:
            problems.append(f"update {i}: {ref or '(no invoice)'} isn't one of your issued invoices")
            continue
        shown = target.get("reference") or target["number"]
        versions = [m for m, rows in lists for r in rows if r["number"] == target["number"]]
        if versions[0]["period"] != period:
            problems.append(f"update {i}: {shown} was issued in {versions[0]['period']}. Use --period {versions[0]['period']}.")
            continue
        lines = build_lines(f"update {i}", up.get("lines", []))
        if not lines and not up.get("cancel"):
            problems.append(f"update {i}: {shown} has no billable lines. To cancel the whole invoice, say so with \"cancel\": true.")
            continue
        total = sum((l["amount"] for l in lines), ZERO)
        paid = _paid_so_far(folder, target["number"], {m["file"] for m in versions})
        if paid is None:
            problems.append(f"update {i}: {shown} is already paid, so it stays as it is. Adjust the client's future invoices.")
        elif total < paid:
            problems.append(f"update {i}: {shown} already has {money_text(paid)} paid, so it can't go down to {money_text(total)}. "
                            "Adjust the client's future invoices.")
        elif total == money(target["amount"]):
            problems.append(f"update {i}: {shown} is already {money_text(total)}, so there's nothing to update.")
        else:
            nth = len(versions)
            cid = target["client_id"]
            docs.append({"kind": "update", "number": target["number"], "shown": shown, "client_id": cid,
                         "client": target["client"], "phone": clients.get(cid, {}).get("phone", ""),
                         "payer": up.get("payer", target.get("payer", "")).strip(), "applies_to": target["number"],
                         "date": target["date"], "was": money(target["amount"]), "lines": lines, "total": total,
                         "suffix": " (updated)" if nth == 1 else f" (updated {nth})"})

    if problems:
        raise Refused("\n".join(problems))
    return {"folder": folder, "factory": factory, "me": me, "biz": biz, "period": period, "date": issue_date,
            "list_name": list_name, "docs": docs}


# ---------- the PDF: one fixed layout for every coach ----------

def _fonts(factory: Path) -> dict:
    """Inter (the business's invoice font) when its files are in factory/invoice-template/fonts/, else Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    names = {"regular": "Inter-Regular", "medium": "Inter-Medium", "semibold": "Inter-SemiBold", "bold": "Inter-Bold"}
    fallback = {"regular": "Helvetica", "medium": "Helvetica", "semibold": "Helvetica-Bold", "bold": "Helvetica-Bold"}
    folder = factory / "invoice-template" / "fonts"
    if not all((folder / f"{n}.ttf").exists() for n in names.values()):
        return fallback
    for n in names.values():
        if n not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(n, str(folder / f"{n}.ttf")))
    return names


def render(path: Path, doc: dict, run: dict) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen.canvas import Canvas

    biz, me = run["biz"], run["me"]
    F = _fonts(run["factory"])
    ink, grey, rule, fill = HexColor("#111827"), HexColor("#6B7280"), HexColor("#E5E7EB"), HexColor("#F3F4F6")
    W, H = A4
    L, R = 39, W - 38
    date = nice_date(doc.get("date") or run["date"])
    c = Canvas(str(path), pagesize=A4, pageCompression=1)          # compressed: small enough to pile up for years
    c.setTitle(f"Invoice {doc['shown']}")
    c.setAuthor(biz.get("trading_name", ""))

    def text(x, top, s, font, size, colour=ink, align="l"):
        """Draw with `top` measured down from the top of the page, as on the original."""
        c.setFont(F[font], size)
        c.setFillColor(colour)
        (c.drawRightString if align == "r" else c.drawCentredString if align == "c" else c.drawString)(x, H - top, s)

    # header
    text(L, 59, "INVOICE", "bold", 20)
    text(R, 55.5, biz.get("trading_name", ""), "semibold", 11.2, align="r")
    text(L, 95, biz.get("trading_name", ""), "medium", 13.5)
    for k, line in enumerate(x for x in (biz.get("website", ""), me.get("phone", ""), me.get("email", "")) if x):
        text(L, 114 + k * 11.7, line, "regular", 8, grey)                 # the coach's own phone and email

    # bill-to box
    c.setStrokeColor(rule)
    c.setLineWidth(0.7)
    c.roundRect(L + 0.5, H - 256, R - L - 0.5, 92, 4, stroke=1, fill=0)
    text(L + 9.5, 180.5, "BILL TO", "bold", 6.5)
    text(L + 9.5, 200, doc["client"], "medium", 11.5)
    if doc.get("phone"):
        text(L + 9.5, 217.5, doc["phone"], "regular", 8, grey)
    labels = [("INVOICE #", doc["shown"]), ("ISSUED", date), ("DUE", date)]
    for k, (label, value) in enumerate(labels):
        text(420, 180.5 + k * 26, label, "bold", 6.5, align="r")
        text(R - 9, 184 + k * 26, value, "regular", 8.5, align="r")

    # items
    cols = [(L + 7, "ITEM", "l"), (363.5, "PRICE", "c"), (442, "QUANTITY", "c"), (R - 6.5, "AMOUNT", "r")]

    def items_head(top):
        c.setFillColor(fill)
        c.roundRect(L + 0.5, H - top - 21.5, R - L - 0.5, 21.5, 4, stroke=0, fill=1)
        for x, label, align in cols:
            text(x, top + 13.5, label, "bold", 6.5, align=align)
        return top + 38

    top = items_head(279.5)
    for ln in doc["lines"]:
        item = simpleSplit(ln["item"], F["regular"], 9.5, 363.5 - 40 - (L + 7))
        if top + 12 * len(item) > H - 300:
            c.showPage()
            top = items_head(48)
        values = [item[0], money_text(ln["price"]), f"{ln['qty'].normalize():f}", money_text(ln["amount"])]
        for (x, _, align), value in zip(cols, values):
            text(x, top, value, "regular", 9.5, align=align)
        for extra in item[1:]:
            top += 12
            text(cols[0][0], top, extra, "regular", 9.5)
        top += 31.7

    # totals
    top += 6
    c.setStrokeColor(rule)
    c.line(299, H - top, R, H - top)
    total = money_text(doc["total"])
    text(305.5, top + 12.5, "Subtotal", "regular", 8.5)
    text(R - 6.5, top + 12.5, total, "regular", 8.5, align="r")
    text(305.5, top + 30.5, "Total", "regular", 8.5)
    text(R - 6.5, top + 30.5, total, "regular", 8.5, align="r")
    text(337, top + 73, "Amount Due", "semibold", 12)
    text(R - 6.5, top + 73, total, "semibold", 12, align="r")
    top += 112

    # payment instruction and sign-off: the business's own words, from factory/business.md
    text(L, top, "Payment Instruction", "medium", 8.5)
    top += 17
    instruction = biz.get("payment_instruction", "").replace("{reference}", doc["shown"])
    bank = simpleSplit(instruction, F["regular"], 8.5, R - L) + [
        biz.get("account_holder", ""), biz.get("bank", ""), f"Branch {biz.get('branch_code', '')}".strip(),
        f"{biz.get('account_type', '')} {biz.get('account_number', '')}".strip()]
    for line in (x for x in bank if x and x != "Branch"):              # long wording wraps inside the margins
        text(L, top, line, "regular", 8.5)
        top += 11.9
    top += 56
    for para in (x for x in (biz.get("pop_request", ""), biz.get("thanks", ""), biz.get("sign_off", "")) if x):
        for line in simpleSplit(para, F["regular"], 8.5, R - L):
            text(L, top, line, "regular", 8.5)
            top += 11.9
        top += 12.1
    c.showPage()
    c.save()


# ---------- issuing ----------

def pdf_name(doc: dict) -> str:
    return f"Invoice {re.sub(r'[#/]+', '', doc['shown']).strip()}{doc.get('suffix', '')}.pdf"


def issue(run: dict) -> Path:
    folder, period = run["folder"], run["period"]
    pdf_dir = folder / "invoices" / period                    # made by the head coach's side when the run opened
    rows = []
    for doc in run["docs"]:                                     # 1. the PDFs
        pdf = pdf_dir / pdf_name(doc)
        render(pdf, doc, run)
        rows.append({"number": doc["number"], "date": doc.get("date") or run["date"], "client_id": doc["client_id"], "client": doc["client"],
                     "payer": doc.get("payer", ""), "reference": doc["shown"], "amount": fmt(doc["total"]),
                     "applies_to": doc.get("applies_to", ""), "pdf": str(pdf.relative_to(folder)),
                     "pdf_sha": file_hash(pdf), "pdf_bytes": pdf.stat().st_size})
    out = folder / "invoice-lists" / run["list_name"]           # 2. the list, last: its existence means "done"
    meta = {"coach": run["me"].get("slug", ""), "period": period, "issued": run["date"]}
    # the seal: recon trusts only lists this generator made, unchanged since (see crm/books.py)
    rows = [{c: str(r.get(c, "")) for c in LIST_COLUMNS} for r in rows]
    write_sheet(out, LIST_COLUMNS, rows, title=f"Invoice list: {run['me'].get('name', '')}, {period}",
                notes=["Made by the invoice generator with the PDFs. Never edited after issue."],
                meta=dict(meta, made_by=GENERATOR, seal=list_seal(meta, rows)))
    return out


NEEDS = ["{coach}/{slug}.me  (Doc, as .txt)", "{coach}/clients  (Sheet, as .csv)", "{coach}/invoice-lists/*  (Sheets, as .csv)",
         "{coach}/unpaid  (Sheet, as .csv)",
         "factory/business  (Doc, as .txt)", "factory/billable-work  (Sheet, as .csv)",
         "factory/invoicing-runs  (Sheet, as .csv)", "factory/invoice-template/fonts/*.ttf  (copy from the downloaded repo's _templates, not the drive)",
         "{coach}/invoices/<month>/   (folder only: check it exists on the drive and make the same empty folder in the "
         "working copy; never create it on the drive)"]


def uploads(run: dict, out: Path) -> str:
    """What to put back on the drive through the connector, in order: the PDFs, then the list (its existence = done)."""
    coach = run["folder"].name
    lines = ["Upload, in this order, then lock each file read-only:"]
    for doc in run["docs"]:
        lines.append(f"  {coach}/invoices/{run['period']}/{pdf_name(doc)}   (application/pdf)")
    lines.append(f"  {coach}/invoice-lists/{out.stem}   (a new Google Sheet, from {out.name}) — LAST")
    return "\n".join(lines)


def summary(run: dict) -> str:
    out = [f"{run['me'].get('name')} — {run['period']} — dated {nice_date(run['date'])} — list {run['list_name']}"]
    for d in run["docs"]:
        who = d["client"] + (f" (paid by {d['payer']})" if d.get("payer") else "")
        what = f"was {money_text(d['was'])}" if d["kind"] == "update" else f"{len(d['lines'])} line(s)"
        out.append(f"  {d['shown']:<14} {who:<40} {what:<20} {money_text(d['total']):>12}")
    invoices = [d for d in run["docs"] if d["kind"] == "invoice"]
    out.append(f"  {len(invoices)} invoice(s), total {money_text(sum((d['total'] for d in invoices), ZERO))}"
               + (f"; {len(run['docs']) - len(invoices)} updated" if len(run["docs"]) > len(invoices) else ""))
    if not run["docs"]:
        out.append("  Nothing to bill: an empty list will mark the run done.")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="the Shared Drive as this coach sees it, or a working copy of it")
    ap.add_argument("--coach-dir", required=True)
    ap.add_argument("--needs", action="store_true", help="list the drive files the generator reads, and stop")
    ap.add_argument("--period")
    ap.add_argument("--drafts", help="approved drafts JSON, or - for stdin")
    ap.add_argument("--date", help="invoice date (default: invoice_day in factory/business.md)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--extra", action="store_true", help="a second list for a period that's already issued")
    a = ap.parse_args()
    if a.needs:
        print("Download these into the working copy, keeping the same folders:")
        print("\n".join("  " + n.format(coach=a.coach_dir, slug=a.coach_dir.removeprefix("coach-")) for n in NEEDS))
        return
    if not (a.root and a.period and a.drafts):
        ap.error("--root, --period and --drafts are needed to issue")
    drafts = json.load(sys.stdin if a.drafts == "-" else open(a.drafts, encoding="utf-8"))
    try:
        run = plan(Path(a.root).expanduser(), a.coach_dir, a.period, drafts, a.date, a.extra)
    except Refused as e:
        print("Refused — nothing issued:\n" + "\n".join("  " + l for l in str(e).splitlines()))
        sys.exit(1)
    print(("DRY RUN — nothing written\n" if a.dry_run else "") + summary(run))
    if not a.dry_run:
        out = issue(run)
        print(f"Issued: {len(run['docs'])} PDF(s) in invoices/{run['period']}/, list {out.relative_to(run['folder'])}")
        print(uploads(run, out))


if __name__ == "__main__":
    main()
