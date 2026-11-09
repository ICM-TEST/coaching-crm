#!/usr/bin/env python3
"""The head coach's list of coaches: add a coach, see the list, mark a coach as left.

  coaches.py --root <drive> add --name "<full name>" --phone "<phone>" --email <email> [--google <google account>]
                                 [--invoice-start <next invoice number>]
  coaches.py --root <drive> list
  coaches.py --root <drive> share <slug>          the head coach's steps to share the coach's folders
  coaches.py --root <drive> welcome <slug>        the coach's step-by-step setup message, their Project instruction inside
  coaches.py --root <drive> leave <slug>          marks them as left; their active clients become unallocated
  coaches.py --root <drive> unshare <slug>        the head coach's steps to remove the coach's access
  coaches.py --root <drive> instructions <slug>   a coach's Project instruction on its own

`add` gives the coach the next coach number (01, 02, …; never reused), creates and names their folder from the
template, writes their <slug>.me Doc and client list Sheet, and prints the Project instruction for that coach's Claude: it names
who that Claude works for. The head coach shares the folders by hand; `share`, `welcome` and `unshare` print the
step-by-step texts from roles/head-coach/coach-steps.md. Head coach only: needs hub/.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import build_client_lists, build_me_files  # noqa: E402
from crm.common import Drive, append_rows, frontmatter, read_table, rewrite_table, today  # noqa: E402

COLUMNS = ["number", "slug", "code", "name", "phone", "email", "invoice_start", "active", "google_account"]
HISTORY_COLUMNS = ["date", "client_id", "change", "reason"]
STEPS = Path(__file__).resolve().parent.parent / "roles" / "head-coach" / "coach-steps.md"
REPO_URL = "https://github.com/ICM-TEST/coaching-crm"
TEMPLATE = Path(__file__).resolve().parent.parent / "_templates" / "drive" / "coach-template"


def add(drive: Drive, name: str, phone: str, email: str, invoice_start: str, slug: str, code: str, google: str = "") -> int:
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
                                                     "active": "yes", "google_account": google or email}])
    build_me_files(drive)
    build_client_lists(drive)
    print(f"Added {name} as coach {number:02d} (folder coach-{slug}/, code {code}).")
    print(f"Next, once it's written to the drive: `coaches.py share {slug}` (the head coach shares the folders), then "
          f"`coaches.py welcome {slug}` (the coach's setup message).")
    return 0


def steps(drive: Drive, slug: str, part: str) -> str:
    """One of the texts in coach-steps.md (share, welcome or unshare), filled in for this coach."""
    row = next((r for r in drive.coaches(active_only=False) if r["slug"] == slug), None)
    if not row:
        raise SystemExit(f"No coach '{slug}' in hub/coaches.")
    text = STEPS.read_text(encoding="utf-8").split(f"\n## {part}\n", 1)[1].split("\n## ", 1)[0].strip()
    head = frontmatter(drive.head_me()).get("name") or "the head coach"
    fill = {"first": row["name"].split()[0], "name": row["name"], "number": row["number"], "folder": f"coach-{slug}",
            "google": row.get("google_account") or row.get("email") or "their Google account",
            "business": frontmatter(drive.factory / "business.txt").get("trading_name", "the business"),
            "head": head.split()[0], "repo": REPO_URL, "instruction": instruction(drive, slug) if part == "welcome" else ""}
    for key, value in fill.items():
        text = text.replace("{" + key + "}", value)
    return text


def instruction(drive: Drive, who: str) -> str:
    """A coach's Project instruction. It names who that Claude works for; the repo's CLAUDE.md then checks the name
    against what the account can open in the Shared Drive. The head coach's instruction names only the role, so it
    isn't made here."""
    business = frontmatter(drive.factory / "business.txt").get("trading_name", "the business")
    if who == "head-coach":
        raise SystemExit("The head coach's instruction names only the role, never a person, so there's nothing to make "
                         "here. It's the same for every business.")
    row = next((r for r in drive.coaches(active_only=False) if r["slug"] == who), None)
    if not row:
        raise SystemExit(f"No coach '{who}' in hub/coaches.")
    return (f"You are the Claude for {row['name']}, coach {row['number']} at {business}.\n\n"
            "Structure: the repository in this project's knowledge. Read workspace/CLAUDE.md before anything else and "
            "follow it, in the coach role. It is read-only.\n\n"
            f"Data: coach-{row['slug']}/ and factory/ in Google Drive, shared with you. Use the Google Drive connector to find "
            "and read files and upload PDFs, Google Sheets for lists, and Google Docs for documents. If you can open hub/ or any other "
            f"coach's folder, or coach-{row['slug']}/{row['slug']}.me doesn't name {row['name']}, coach {row['number']}, stop "
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
    """The coach is marked as left (their number is never reused), and every active or new client of theirs becomes
    unallocated, so the head coach can see who needs a new coach. Their folder and invoices stay."""
    path = drive.hub / "coaches.csv"
    rows = read_table(path)
    coach = next((r for r in rows if r["slug"] == slug), None)
    if not coach:
        print(f"Refused: no coach '{slug}'.")
        return 1
    coach["active"] = "no"
    rewrite_table(path, COLUMNS, rows)
    clients_path = drive.hub / "clients.csv"
    clients = read_table(clients_path)
    theirs = [c for c in clients if c.get("coach") == slug and c.get("status") in ("active", "new")]
    for c in theirs:
        c["status"] = "unallocated"                     # `coach` keeps their last coach, so the head coach sees who it was
    if theirs:
        rewrite_table(clients_path, list(clients[0].keys()), clients)
        append_rows(drive.hub / "client-history.csv", HISTORY_COLUMNS,
                    [{"date": today(), "client_id": c["id"], "change": f"coach {slug} → unallocated",
                      "reason": f"{coach['name']} left"} for c in theirs])
    build_me_files(drive)
    build_client_lists(drive)
    print(f"{coach['name']} (coach {coach['number']}) is marked as left. Their folder and invoices stay, and the bank "
          "recon still matches payments to their invoices.")
    if theirs:
        print(f"{len(theirs)} client(s) are now unallocated and need a new coach:")
        for c in theirs:
            print(f"  {c['id']}  {c['name']}")
    print(f"Next, once it's written to the drive: `coaches.py unshare {slug}` (the head coach removes their access).")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--name", required=True); a.add_argument("--phone", default=""); a.add_argument("--email", default="")
    a.add_argument("--invoice-start", default="1"); a.add_argument("--slug", default=""); a.add_argument("--code", default="")
    a.add_argument("--google", default="", help="the Google account to share with, if not --email")
    sub.add_parser("list")
    l = sub.add_parser("leave"); l.add_argument("slug")
    for part in ("share", "welcome", "unshare"):
        sub.add_parser(part).add_argument("slug")
    i = sub.add_parser("instructions"); i.add_argument("who", help="a coach's slug")
    args = ap.parse_args()
    drive = Drive(args.root)
    if args.cmd == "add":
        sys.exit(add(drive, args.name, args.phone, args.email, args.invoice_start, args.slug, args.code.upper(), args.google))
    if args.cmd in ("share", "welcome", "unshare"):
        print(steps(drive, args.slug, args.cmd))
        sys.exit(0)
    if args.cmd == "instructions":
        print(instruction(drive, args.who))
        sys.exit(0)
    sys.exit(show(drive) if args.cmd == "list" else leave(drive, args.slug))


if __name__ == "__main__":
    main()
