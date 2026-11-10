#!/usr/bin/env python3
"""scan.py: the personal-data scan every public structure repo passes before a release. Ross only.

    python3 tools/scan.py [--denylist <file>]

The same file, byte for byte, in every client repo. It reads every tracked and untracked (not ignored) text file and
reports: a phrase from the deny list, an email address that isn't made up, anything shaped like a secret.

The deny list names real people and businesses, so it never lives in a repo. It is looked for in this order:
--denylist, $ICM_DENYLIST, then `_system/reference/public-repo-denylist.txt` in any folder above this repo (Ross's
workspace). One phrase per line; `#` starts a comment. A repo whose own subject uses a listed word (a sport, say) lists
that word in `tools/scan-allow.txt`, which is public: it must never hold a name.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHARED = "_system/reference/public-repo-denylist.txt"
ALLOW = REPO / "tools" / "scan-allow.txt"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOKEN = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16})\b")
SKIP = {"scan.py", "release.py"}                     # the tools that describe the patterns


class Refused(Exception):
    pass


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


def _lines(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def load_denylist(path: str | None = None, repo: Path = REPO) -> list[str]:
    found = path or os.environ.get("ICM_DENYLIST") or os.environ.get("CRM_DENYLIST")
    if not found:
        found = next((str(up / SHARED) for up in repo.resolve().parents if (up / SHARED).exists()), None)
    if not found or not Path(found).exists():
        raise Refused(f"No deny list found ({found or SHARED + ' above this repo'}). Give one with --denylist.")
    allow = {a.lower() for a in _lines(ALLOW)} if ALLOW.exists() else set()
    return [p for p in _lines(Path(found)) if p.lower() not in allow]


def scan(deny: list[str], repo: Path = REPO) -> list[str]:
    def git(*args: str) -> list[str]:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.splitlines()
    names = {*git("ls-files"), *git("ls-files", "--others", "--exclude-standard")}
    problems = []
    for name in sorted(names):
        p = repo / name
        if p.name in SKIP or not p.is_file():
            continue
        try:
            problems += scan_text(name, p.read_text(encoding="utf-8"), deny)
        except UnicodeDecodeError:
            continue
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--denylist")
    a = ap.parse_args()
    try:
        deny = load_denylist(a.denylist)
    except Refused as e:
        print(f"Refused: {e}")
        return 1
    problems = scan(deny)
    print("\n".join(problems) if problems else f"Scan clean ({len(deny)} deny-list phrases).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
