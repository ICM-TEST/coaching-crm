#!/usr/bin/env python3
"""Invoicing runs: the gate in front of the month-end recon.

  runs.py --root <drive> open 2026-11 [--due 2026-11-24]   head coach (default: invoice_day in factory/business)
  runs.py --root <drive> status 2026-11                     head coach

A coach is done when an invoice list for the period exists in their invoice-lists/.
There is no separate "done" mark: the list is the state.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import invoice_lists  # noqa: E402
from crm.common import ZERO, Drive, append_rows, fmt, frontmatter, money, read_table, today  # noqa: E402

RUN_COLUMNS = ["period", "opened", "due", "status"]


def gate(drive: Drive, period: str) -> tuple[list[dict], list[dict]]:
    """(done, not_done) among active coaches for the period."""
    done, missing = [], []
    for coach in drive.coaches(active_only=True):
        lists = [(m, rows) for m, rows in invoice_lists(drive.coach_dir(coach["slug"]))
                 if m["period"] == period and not m["problem"]]                # only lists the generator sealed count
        if not lists:
            missing.append(coach)
            continue
        rows = list({r["number"]: r for _, r_ in lists for r in r_}.values())     # an update replaces its invoice
        invoices = [r for r in rows if money(r.get("amount")) > ZERO]
        done.append(dict(coach, issued=min(m.get("issued", "") for m, _ in lists), invoices=len(invoices),
                         total=fmt(sum((money(r["amount"]) for r in rows), ZERO))))
    return done, missing


def cmd_open(root, period: str, due: str | None) -> None:
    drive = Drive(root)
    if not due:
        day = int(frontmatter(drive.factory / "business.txt").get("invoice_day") or 24)
        due = f"{period}-{day:02d}"
    path = drive.factory / "invoicing-runs.csv"
    # The head coach's side makes every folder; a coach's Claude never does. Each active coach gets this month's
    # PDF folder now, so their invoices have somewhere to go (also for a run that's already open).
    made = []
    for coach in drive.coaches(active_only=True):
        folder = drive.coach_dir(coach["slug"]) / "invoices" / period
        if drive.coach_dir(coach["slug"]).is_dir() and not folder.is_dir():
            folder.mkdir(parents=True)
            made.append(coach["slug"])
    if made:
        print(f"Made invoices/{period}/ for: {', '.join(made)}")
    if any(r.get("period") == period for r in read_table(path)):
        print(f"{period} is already open.")
        return
    append_rows(path, RUN_COLUMNS, [{"period": period, "opened": today(), "due": due, "status": "open"}])
    print(f"Opened {period}, due {due}. Tag every active coach on factory/invoicing-runs.")


def cmd_status(root, period: str) -> None:
    drive = Drive(root)
    done, missing = gate(drive, period)
    total = len(done) + len(missing)
    print(f"{period}: {len(done)} of {total} done — {'COMPLETE' if not missing else 'NOT COMPLETE'}")
    for c in done:
        print(f"  done      {c['name']:<12} {c['invoices']:>3} invoices  {c['total']:>10}  (issued {c['issued']})")
    for c in missing:
        print(f"  NOT DONE  {c['name']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open"); o.add_argument("period"); o.add_argument("--due")
    s = sub.add_parser("status"); s.add_argument("period")
    args = ap.parse_args()
    if args.cmd == "open":
        cmd_open(args.root, args.period, args.due)
    else:
        cmd_status(args.root, args.period)


if __name__ == "__main__":
    main()
