#!/usr/bin/env python3
"""release.py: ship a structure change. Ross only. The same file, byte for byte, in every client repo.

    python3 tools/release.py --note "what changed" [--bump patch|minor|major] [--dry-run]
    python3 tools/release.py --scan-only

In order, stopping at the first failure: personal-data scan, clean tree, every tools/tests/test_*.py, version bump in
workspace/version.md, commit "Release vX.Y.Z: note", tag vX.Y.Z, push the branch and the tag. The repo is public, so
the scan must pass: tools/scan.py says where its deny list lives. What happens after the push (how the client hears
about it) is the one step that differs per repo: README.md § Changing the live system.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSION = REPO / "workspace/version.md"
MARKER = REPO / "_templates/drive/factory/release.txt"     # only in repos whose drive template carries the version
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan import Refused, load_denylist, scan, scan_text  # noqa: E402,F401


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
        tests = sorted((REPO / "tools/tests").glob("test_*.py"))
        if not tests:
            raise Refused("No tests in tools/tests/: a repo with no tests isn't released.")
        for t in tests:
            p = subprocess.run([sys.executable, "-B", str(t)], capture_output=True, text=True)
            if p.returncode:
                raise Refused(f"{t.name} failed:\n{p.stdout[-800:]}{p.stderr[-800:]}")
        text = VERSION.read_text()
        new = bump(re.search(r"^version: (.*)$", text, re.M).group(1).strip(), a.bump)
        if a.dry_run:
            print(f"Dry run: {len(tests)} test file(s) pass; would release {new}.")
            return
        VERSION.write_text(bumped_version_file(text, new, dt.date.today().isoformat(), a.note))
        changed = [str(VERSION)]
        if MARKER.exists():
            MARKER.write_text(re.sub(r"^version: .*$", f"version: {new}", MARKER.read_text(), count=1, flags=re.M))
            changed.append(str(MARKER))
        git("add", *changed)
        git("commit", "-m", f"Release v{new}: {a.note}")
        git("tag", "-a", f"v{new}", "-m", f"Release v{new}: {a.note}")
        git("push", "origin", "HEAD", f"v{new}")
        print(f"Released {new}, tagged v{new}. Now tell the client: README.md § Changing the live system.")
    except Refused as e:
        print(f"Refused: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
