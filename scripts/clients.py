#!/usr/bin/env python3
"""The head coach's list of clients: which details it keeps, and bringing in a list the business already has.

  clients.py --root <drive> details                         the details the list keeps
  clients.py --root <drive> details --add "<detail>" ...    add details of the head coach's own (extra columns)
  clients.py --root <drive> import <file.csv> --dry-run     check an existing list before anything is added
  clients.py --root <drive> import <file.csv>               add it: next client ids, status active, or unallocated
                                                            when no coach is given

The file to import is a CSV the head coach's Claude makes from whatever list the business has. Its header row uses
these names: name, phone, email, coach (a coach's name or slug, or blank), notes, and any of the head coach's own
details, spelled exactly as `details` shows them. Only name is required.

The head coach's own details live only in hub/clients: coaches' client lists never show them.
Head coach only: needs hub/.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import build_client_lists  # noqa: E402
from crm.common import Drive, _split, append_rows, read_table, rewrite_table, today  # noqa: E402

FIXED = ["id", "name", "phone", "email", "status", "coach", "since", "notes"]
IMPORTABLE = ["name", "phone", "email", "coach", "notes"]
HISTORY_COLUMNS = ["date", "client_id", "change", "reason"]


def columns(drive: Drive) -> list[str]:
    """The list's columns: the fixed ones, then the head coach's own details."""
    _, table = _split(drive.hub / "clients.csv")
    return [h.strip() for h in table[0]] if table else list(FIXED)


def details(drive: Drive, add: list[str]) -> int:
    path, cols = drive.hub / "clients.csv", columns(drive)
    known = {c.lower() for c in cols}
    new = []
    for d in (" ".join(a.split()) for a in add):
        if not d:
            continue
        if d.lower() in known:
            print(f"Refused: the list already keeps '{d}'.")
            return 1
        new.append(d)
        known.add(d.lower())
    if new:
        rewrite_table(path, cols + new, read_table(path))
        cols += new
        print("Added: " + ", ".join(new))
    extras = [c for c in cols if c not in FIXED]
    print("Every client has: name, phone, email, coach, status, since, notes.")
    print("The head coach's own details: " + (", ".join(extras) if extras else "none yet."))
    return 0


def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def import_(drive: Drive, file: Path, dry_run: bool) -> int:
    cols = columns(drive)
    extras = [c for c in cols if c not in FIXED]
    _, table = _split(file)
    header = [h.strip() for h in table[0]] if table else []
    rows = read_table(file)
    problems, warnings = [], []
    if "name" not in header:
        problems.append("the file has no 'name' column")
    unknown = [h for h in header if h and h not in IMPORTABLE + extras]
    if unknown:
        problems.append("columns the list doesn't keep: " + ", ".join(unknown) + ". Add them first (details --add), "
                        "or leave them out")
    coaches = drive.coaches(active_only=True)
    by_key = {c["slug"].lower(): c["slug"] for c in coaches}
    by_key.update({c["name"].lower(): c["slug"] for c in coaches})
    firsts: dict[str, list[str]] = {}
    for c in coaches:
        firsts.setdefault(c["name"].split()[0].lower(), []).append(c["slug"])
    by_key.update({k: v[0] for k, v in firsts.items() if len(v) == 1 and k not in by_key})

    existing = read_table(drive.hub / "clients.csv")
    seen_phone = {_digits(c.get("phone", "")): c["name"] for c in existing if len(_digits(c.get("phone", ""))) >= 7}
    seen_email = {c.get("email", "").strip().lower(): c["name"] for c in existing if c.get("email", "").strip()}
    seen_pair = {(c["name"].strip().lower(), _digits(c.get("phone", ""))) for c in existing}
    numbers = [int(c["id"][1:]) for c in existing if re.fullmatch(r"C\d+", c.get("id", ""))]
    next_no = max(numbers, default=0) + 1
    new_rows, counts = [], {}
    for n, r in enumerate(rows, 2):                                   # line 1 is the header
        name = " ".join((r.get("name") or "").split())
        if not name:
            problems.append(f"line {n}: no name")
            continue
        phone, email = (r.get("phone") or "").strip(), (r.get("email") or "").strip()
        given = " ".join((r.get("coach") or "").split())
        slug = by_key.get(given.lower(), "") if given else ""
        if given and not slug:
            problems.append(f"line {n} ({name}): no active coach called '{given}'")
            continue
        pair = (name.lower(), _digits(phone))
        if pair in seen_pair:
            problems.append(f"line {n} ({name}): already in the list, or twice in this file")
            continue
        if not phone:
            warnings.append(f"line {n} ({name}): no phone. It's printed on invoices, so add it later")
        elif len(_digits(phone)) >= 7 and _digits(phone) in seen_phone:
            warnings.append(f"line {n} ({name}): same phone as {seen_phone[_digits(phone)]}. Family, or a duplicate?")
        if email and email.lower() in seen_email:
            warnings.append(f"line {n} ({name}): same email as {seen_email[email.lower()]}. Family, or a duplicate?")
        seen_pair.add(pair)
        if len(_digits(phone)) >= 7:
            seen_phone.setdefault(_digits(phone), name)
        if email:
            seen_email.setdefault(email.lower(), name)
        row = {c: (r.get(c) or "").strip() for c in extras}
        row.update({"id": f"C{next_no:04d}", "name": name, "phone": phone, "email": email,
                    "status": "active" if slug else "unallocated", "coach": slug, "since": today(),
                    "notes": (r.get("notes") or "").strip()})
        next_no += 1
        new_rows.append(row)
        label = next((c["name"] for c in coaches if c["slug"] == slug), "unallocated (no coach yet)")
        counts[label] = counts.get(label, 0) + 1

    print(f"{len(new_rows)} client(s) ready to add:")
    for label, k in sorted(counts.items()):
        print(f"  {label}: {k}")
    for w in warnings:
        print(f"  Check: {w}")
    if problems:
        print("Refused. Fix these in the file and check it again:\n  " + "\n  ".join(problems))
        return 1
    if dry_run:
        print("Nothing added yet (dry run).")
        return 0
    append_rows(drive.hub / "clients.csv", cols, new_rows)
    append_rows(drive.hub / "client-history.csv", HISTORY_COLUMNS,
                [{"date": today(), "client_id": r["id"], "change": f"imported, coach {r['coach'] or 'unallocated'}",
                  "reason": "the business's existing client list"} for r in new_rows])
    build_client_lists(drive)
    print(f"Added {len(new_rows)} client(s): {new_rows[0]['id']} to {new_rows[-1]['id']}." if new_rows else "Added nothing.")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("details")
    d.add_argument("--add", nargs="+", default=[])
    i = sub.add_parser("import")
    i.add_argument("file")
    i.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    drive = Drive(a.root)
    sys.exit(details(drive, a.add) if a.cmd == "details" else import_(drive, Path(a.file).expanduser(), a.dry_run))


if __name__ == "__main__":
    main()
