#!/usr/bin/env python3
"""Who's done a month's invoicing: the gate in front of the month-end recon.

  runs.py --root <drive> status 2026-11      head coach

Nobody opens a month. Each coach's Claude makes its own month folder (invoices/<YYYY-MM>/) the first time it issues
for that month, and a coach is done when a sealed invoice list for the month exists in their invoice-lists/. There is
no separate "done" mark: the list is the state. Invoices are due on invoice_day in factory/business.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import invoice_lists  # noqa: E402
from crm.common import ZERO, Drive, fmt, frontmatter, money  # noqa: E402


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


def due_date(drive: Drive, period: str) -> str:
    """The month's invoice day, from factory/business, or '' if it isn't set."""
    day = str(frontmatter(drive.factory / "business.txt").get("invoice_day", "")).strip()
    return f"{period}-{int(day):02d}" if day.isdigit() else ""


def cmd_status(root, period: str) -> None:
    drive = Drive(root)
    done, missing = gate(drive, period)
    total, due = len(done) + len(missing), due_date(drive, period)
    print(f"{period}{', due ' + due if due else ''}: {len(done)} of {total} done — "
          f"{'COMPLETE' if not missing else 'NOT COMPLETE'}")
    for c in done:
        print(f"  done      {c['name']:<12} {c['invoices']:>3} invoices  {c['total']:>10}  (issued {c['issued']})")
    for c in missing:
        print(f"  NOT DONE  {c['name']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("period")
    args = ap.parse_args()
    cmd_status(args.root, args.period)


if __name__ == "__main__":
    main()
