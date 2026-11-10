#!/usr/bin/env python3
"""release.py: ship a structure change. Ross only.

    python3 tools/release.py --note "what changed" [--bump minor] [--dry-run]
    python3 tools/release.py --scan-only

In order, stopping at the first failure: personal-data scan, clean tree, all tests, version bump, commit, tag
vX.Y.Z, push the branch and the tag. The same order in every client repo (Ross's push checklist). The repo is public,
so the scan must pass: tools/scan.py says where its deny list lives. The tag is what each job downloads its scripts
from (workspace/shared/connectors.md step 0), so the rules a Project holds and the code it runs are always one version.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSION = REPO / "workspace/version.md"
TEMPLATE = REPO / "_templates/drive/factory/release.txt"
TESTS = ["test_cycle", "test_coaches", "test_issue", "test_sync", "test_updates", "test_setup", "test_release",
         "test_statements", "test_clients", "test_usage"]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan import Refused, load_denylist, scan, scan_text  # noqa: E402,F401  (the same scan in every client repo)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def bump(version: str, part: str) -> str:
    major, minor, patch_ = (int(x) for x in version.split("."))
    return f"{major + 1}.0.0" if part == "major" else f"{major}.{minor + 1}.0" if part == "minor" else f"{major}.{minor}.{patch_ + 1}"


def bumped_version_file(text: str, new: str, today: str, note: str) -> str:
    text = re.sub(r"^version: .*$", f"version: {new}", text, count=1, flags=re.M)
    text = re.sub(r"^released: .*$", f"released: {today}", text, count=1, flags=re.M)
    return text.rstrip() + f"\n- {new} ({today}): {note}\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--note")
    ap.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scan-only", action="store_true")
    ap.add_argument("--denylist")
    a = ap.parse_args()
    try:
        deny = load_denylist(a.denylist)
        problems = scan(deny)
        if problems:
            raise Refused("Personal data scan failed. Nothing released:\n  " + "\n  ".join(problems))
        print(f"Scan clean ({len(deny)} deny-list phrases).")
        if a.scan_only:
            return
        if not a.note:
            raise Refused("--note is needed")
        if git("status", "--porcelain").strip():
            raise Refused("Commit your edits first: the working tree isn't clean.")
        for t in TESTS:
            p = subprocess.run([sys.executable, "-B", str(REPO / "tools/tests" / f"{t}.py")], capture_output=True, text=True)
            if p.returncode:
                raise Refused(f"{t} failed:\n{p.stdout[-800:]}{p.stderr[-800:]}")
        text = VERSION.read_text()
        new = bump(re.search(r"^version: (.*)$", text, re.M).group(1).strip(), a.bump)
        if a.dry_run:
            print(f"Dry run: tests pass; would release {new}.")
            return
        VERSION.write_text(bumped_version_file(text, new, dt.date.today().isoformat(), a.note))
        TEMPLATE.write_text(re.sub(r"^version: .*$", f"version: {new}", TEMPLATE.read_text(), count=1, flags=re.M))
        git("add", str(VERSION), str(TEMPLATE))
        git("commit", "-m", f"Release v{new}: {a.note}")
        git("tag", "-a", f"v{new}", "-m", f"Release v{new}: {a.note}")
        git("push", "origin", "HEAD", f"v{new}")
        print(f"Released {new}. Now tell the head coach's Claude: \"version {new} is out\".")
    except Refused as e:
        print(f"Refused: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
