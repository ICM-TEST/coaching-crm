#!/usr/bin/env python3
"""release.py: ship a structure change. Ross only.

    python3 tools/release.py --note "what changed" [--bump minor] [--dry-run]
    python3 tools/release.py --scan-only

In order, stopping at the first failure: clean tree, all tests, personal-data scan, version bump, commit, push.
The repo is public, so the scan must pass. Its deny list holds real names and lives outside the repo:
--denylist, or $CRM_DENYLIST, one phrase per line.
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
TEMPLATE = REPO / "workspace/_templates/drive/factory/release.txt"
TESTS = ["test_cycle", "test_coaches", "test_issue", "test_sync", "test_updates", "test_setup", "test_release",
         "test_statements", "test_clients"]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOKEN = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16})\b")


class Refused(Exception):
    pass


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def scan_text(name: str, text: str, deny: list[str]) -> list[str]:
    """Personal data or secrets in one file's text."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for phrase in deny:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])", line, re.I):
                out.append(f"{name}:{i}: a phrase from the deny list")
        for mail in EMAIL.findall(line):
            if not re.search(r"(example\.|noreply@)", mail):
                out.append(f"{name}:{i}: an email address")
        if TOKEN.search(line):
            out.append(f"{name}:{i}: what looks like a secret")
    return out


def load_denylist(path: str | None) -> list[str]:
    path = path or os.environ.get("CRM_DENYLIST") or str(REPO.parent.parent / "notes/public-repo-denylist.txt")
    if not Path(path).exists():
        raise Refused(f"No deny list at {path}. Give one with --denylist.")
    return [l.strip() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")]


def scan(deny: list[str]) -> list[str]:
    git("add", "-A", "-n")
    names = {*git("ls-files").splitlines(), *git("ls-files", "--others", "--exclude-standard").splitlines()}
    problems = []
    for name in sorted(names):
        p = REPO / name
        if p.name == "release.py" or not p.is_file():
            continue
        try:
            problems += scan_text(name, p.read_text(encoding="utf-8"), deny)
        except UnicodeDecodeError:
            continue
    return problems


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
        git("commit", "-m", f"Release v{new}: {a.note}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
        git("push")
        print(f"Released {new}. Now tell the head coach's Claude: \"version {new} is out\".")
    except Refused as e:
        print(f"Refused: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
