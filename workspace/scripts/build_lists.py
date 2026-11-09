#!/usr/bin/env python3
"""Rebuild generated lists from the head coach's sources.

  build_lists.py --root <drive> coach-clients   coach list + main list -> each coach's <slug>.me Doc and clients Sheet
  build_lists.py --root <drive> books           allocations -> each coach's unpaid Sheet, hub views

Head coach only: needs hub/.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crm.books import Books, build_client_lists, build_coach_views, build_hub_views, build_me_files  # noqa: E402
from crm.common import Drive  # noqa: E402

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="path to the Shared Drive")
    ap.add_argument("what", choices=["coach-clients", "books"])
    args = ap.parse_args()
    drive = Drive(args.root)
    if args.what == "coach-clients":
        build_me_files(drive)
        changed = build_client_lists(drive)
    else:
        books = Books(drive)
        books.archive_new()                 # the head coach's copy of newly seen sealed invoices
        changed = build_coach_views(drive, books)
        build_hub_views(drive, books)
    print("Changed: " + (", ".join(changed) if changed else "none"))


if __name__ == "__main__":
    main()
