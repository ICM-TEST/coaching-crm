#!/usr/bin/env python3
"""The head coach's list of coaches: add a coach, see the list, mark a coach as left.

  coaches.py --root <drive> add --name "Ayanda Dlamini" --phone "+27..." --email ayanda@... [--invoice-start 212]
  coaches.py --root <drive> list
  coaches.py --root <drive> leave ayanda
  coaches.py --root <drive> instructions ayanda        (or: instructions head-coach)

`add` gives the coach the next coach number (01, 02, …; never reused), creates and names their folder from the
template, writes their me Doc and client list Sheet, and prints the Project instruction for that coach's Claude: it names
who that Claude works for. Sharing the folder is still done by hand: setup/sharing-checklist.md.
Head coach only: needs hub/.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import build_client_lists, build_me_files  # noqa: E402
from crm.common import Drive, append_rows, frontmatter, read_table, rewrite_table  # noqa: E402

COLUMNS = ["number", "slug", "code", "name", "phone", "email", "invoice_start", "active"]
TEMPLATE = Path(__file__).resolve().parent.parent / "_templates" / "drive" / "coach-template"


def add(drive: Drive, name: str, phone: str, email: str, invoice_start: str, slug: str, code: str) -> int:
    rows = drive.coaches(active_only=False)
    numbers = [int(r["number"]) for r in rows if str(r.get("number", "")).isdigit()]
    number = max(numbers, default=0) + 1                        # rows are never deleted, so numbers are never reused
    if number > 99:
        print("Refused: coach numbers run out at 99.")
        return 1
    slugs, codes = {r["slug"] for r in rows}, {r.get("code", "") for r in rows}
    slug = slug or re.sub(r"[^a-z0-9]", "", name.split()[0].lower())
    base, k = slug, 2
    while slug in slugs or drive.coach_dir(slug).exists():
        slug, k = f"{base}{k}", k + 1
    letters = re.sub(r"[^A-Z]", "", name.upper())
    code = code or next((f"{letters[0]}{x}" for x in letters[1:] + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                         if f"{letters[0]}{x}" not in codes), "")
    if not code or code in codes:
        print(f"Refused: give a unique --code (taken: {', '.join(sorted(codes))}).")
        return 1
    shutil.copytree(TEMPLATE, drive.coach_dir(slug))
    append_rows(drive.hub / "coaches.csv", COLUMNS, [{"number": f"{number:02d}", "slug": slug, "code": code, "name": name,
                                                     "phone": phone, "email": email, "invoice_start": invoice_start,
                                                     "active": "yes"}])
    build_me_files(drive)
    build_client_lists(drive)
    print(f"Added {name} as coach {number:02d} (folder coach-{slug}/, code {code}).")
    print(f"Next: share coach-{slug}/ with {email or 'their Google account'} as Contributor, and factory/ as Viewer "
          "(setup/sharing-checklist.md).")
    print(f"Then paste this as the instruction of {name.split()[0]}'s Claude Project:\n\n{instruction(drive, slug)}")
    return 0


def instruction(drive: Drive, who: str) -> str:
    """The Project instruction for one person's Claude. It names who that Claude works for; the repo's CLAUDE.md
    then checks the name against what the account can open in the Shared Drive."""
    business = frontmatter(drive.factory / "business.txt").get("trading_name", "the business")
    drive_name = drive.root.name
    head = frontmatter(drive.hub / "me.txt")
    if who == "head-coach":
        return (f"You are the Claude for {head.get('name', 'the head coach')}, the head coach at {business}. "
                f"You work in the \"{drive_name}\" Shared Drive: hub/ is yours, and your own coaching is in "
                f"coach-{head.get('slug', '')}/. Read workspace/CLAUDE.md, in this project's knowledge, before anything else, and follow the head-coach role. "
                "If you can't open hub/, stop and say so.")
    row = next((r for r in drive.coaches(active_only=False) if r["slug"] == who), None)
    if not row:
        raise SystemExit(f"No coach '{who}' in hub/coaches.")
    return (f"You are the Claude for {row['name']}, coach {row['number']} at {business}. Your folder is "
            f"coach-{row['slug']}/ in the \"{drive_name}\" Shared Drive. Read workspace/CLAUDE.md, in this project's knowledge, before anything else, and follow "
            f"the coach role, working only in coach-{row['slug']}/ and factory/. If you can open hub/ or any other "
            f"coach's folder, or coach-{row['slug']}/me doesn't name {row['name']}, coach {row['number']}, stop "
            f"and tell {row['name'].split()[0]} to alert the head coach.")


def show(drive: Drive) -> int:
    clients = read_table(drive.hub / "clients.csv")
    print(f"{'No.':<4} {'Coach':<22} {'Phone':<16} {'Email':<30} {'Clients':>7}  Active")
    for r in sorted(drive.coaches(active_only=False), key=lambda r: r.get("number", "")):
        n = sum(1 for c in clients if c.get("coach") == r["slug"] and c.get("status") in ("active", "new"))
        print(f"{r.get('number', ''):<4} {r['name']:<22} {r.get('phone', ''):<16} {r.get('email', ''):<30} {n:>7}  "
              f"{r.get('active', '')}")
    return 0


def leave(drive: Drive, slug: str) -> int:
    path = drive.hub / "coaches.csv"
    rows = read_table(path)
    if not any(r["slug"] == slug for r in rows):
        print(f"Refused: no coach '{slug}'.")
        return 1
    for r in rows:
        if r["slug"] == slug:
            r["active"] = "no"
    rewrite_table(path, COLUMNS, rows)
    left = sum(1 for c in read_table(drive.hub / "clients.csv") if c.get("coach") == slug and c.get("status") == "active")
    print(f"{slug} marked as left. Their folder and invoices stay; recon keeps matching payments to them.")
    print(f"Next: remove their access (setup/sharing-checklist.md), and reassign their {left} active client(s).")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--name", required=True); a.add_argument("--phone", default=""); a.add_argument("--email", default="")
    a.add_argument("--invoice-start", default="1"); a.add_argument("--slug", default=""); a.add_argument("--code", default="")
    sub.add_parser("list")
    l = sub.add_parser("leave"); l.add_argument("slug")
    i = sub.add_parser("instructions"); i.add_argument("who", help="a coach's slug, or head-coach")
    args = ap.parse_args()
    drive = Drive(args.root)
    if args.cmd == "add":
        sys.exit(add(drive, args.name, args.phone, args.email, args.invoice_start, args.slug, args.code.upper()))
    if args.cmd == "instructions":
        print(instruction(drive, args.who))
        sys.exit(0)
    sys.exit(show(drive) if args.cmd == "list" else leave(drive, args.slug))


if __name__ == "__main__":
    main()
