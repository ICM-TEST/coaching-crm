#!/usr/bin/env python3
"""Turn a job's changes in the working copy into Google connector steps (Drive, Sheets, Docs).

  sync.py snapshot <work>                                   before the job: remember the working copy as downloaded
  sync.py plan <work> --role coach --coach coach-<slug>      after the job: the steps, in order, for Claude to carry out
  sync.py plan <work> --role head-coach [--json]

In the working copy a Sheet is a .csv and a Doc a .txt (same folders, same names without the extension on the
drive). The plan says, per file: create a folder, upload a PDF, create a Sheet or Doc, append rows to a Sheet, clear and
rewrite a Sheet, replace a Doc's text, add a dropdown, lock a file. It refuses anything the role may not do: a coach's
Claude may only upload its PDFs into a month folder that already exists and create its invoice-list Sheets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

BEFORE = ".before"
SKIP = {BEFORE, ".drive-index.csv"}


def _files(work: Path) -> tuple[set[str], set[str]]:
    files, dirs = set(), set()
    for p in work.rglob("*"):
        rel = p.relative_to(work)
        if rel.parts[0] in SKIP or any(part.startswith(".") for part in rel.parts):
            continue
        (dirs if p.is_dir() else files).add(str(rel))
    return files, dirs


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(work: Path) -> None:
    before = work / BEFORE
    if before.exists():
        shutil.rmtree(before)
    before.mkdir()
    files, dirs = _files(work)
    for rel in files:
        if rel.endswith((".csv", ".txt")):
            (before / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work / rel, before / rel)
    (before / "manifest.json").write_text(json.dumps(
        {"dirs": sorted(dirs), "files": {rel: _sha(work / rel) for rel in sorted(files)}}, indent=1))
    print(f"Snapshot of {len(files)} file(s) in {len(dirs)} folder(s).")


def _csv_rows(text: str) -> list[list[str]]:
    return [r for r in csv.reader(io.StringIO(text))]


def as_written(values: list[list[str]]) -> list[list[str]]:
    """The cells exactly as the Sheets connector must be given them.

    The connector treats what it writes as if a person typed it: a phone number loses its leading zero, a reference like 2026-01-5
    becomes the date 2026-01-05 (which breaks the list's seal), a phone starting with + becomes #ERROR!, and a name starting
    with = runs as a formula. A leading apostrophe on every filled cell makes Sheets keep the rest as plain text. The
    apostrophe isn't part of the value and doesn't come back in the CSV export. Tested on real Sheets, 2026-11-06.
    """
    return [[f"'{cell}" if cell else "" for cell in row] for row in values]


def _drive_name(rel: str) -> str:
    """On the drive, Sheets and Docs have no extension."""
    return rel[:-4] if rel.endswith((".csv", ".txt")) else rel


def plan(work: Path, role: str, coach: str) -> tuple[list[dict], list[str]]:
    before = work / BEFORE
    manifest = json.loads((before / "manifest.json").read_text())
    old_files, old_dirs = manifest["files"], set(manifest["dirs"])
    files, dirs = _files(work)
    ops: list[dict] = []
    for d in sorted(dirs - old_dirs, key=lambda d: d.count("/")):
        ops.append({"op": "create_folder", "path": d})
    lists_last = []
    for rel in sorted(files):
        new = rel not in old_files
        if not new and _sha(work / rel) == old_files[rel]:
            continue
        folder, name = (rel.rsplit("/", 1) + [""])[:2] if "/" in rel else ("", rel)
        if rel.endswith(".csv"):
            values = _csv_rows((work / rel).read_text(encoding="utf-8"))
            if new:
                op = {"op": "create_sheet", "path": _drive_name(rel), "folder": folder, "values": values}
                meta = {r[0].strip()[:-1]: (r[1] if len(r) > 1 else "") for r in values
                        if r and r[0].strip().endswith(":") and not r[0].startswith("#")}
                if meta.get("dropdown"):
                    column, options = meta["dropdown"].split("=", 1)
                    op["dropdown"] = {"column": column, "options": options.split("|")}
                (lists_last if "/invoice-lists/" in f"/{rel}" else ops).append(op)
            else:
                old = _csv_rows((before / rel).read_text(encoding="utf-8"))
                if len(values) > len(old) and values[:len(old)] == old:
                    ops.append({"op": "append", "path": _drive_name(rel), "values": values[len(old):]})
                else:
                    ops.append({"op": "rewrite", "path": _drive_name(rel), "values": values})
        elif rel.endswith(".txt"):
            text = (work / rel).read_text(encoding="utf-8")
            ops.append({"op": "create_doc" if new else "replace_doc", "path": _drive_name(rel), "folder": folder,
                        "text": text})
        else:
            if not new:
                ops.append({"op": "refused", "path": rel, "why": "an uploaded file changed: files are never replaced"})
                continue
            mime = "application/pdf" if rel.endswith(".pdf") else "application/octet-stream"
            ops.append({"op": "upload", "path": rel, "folder": folder, "mime": mime})
    for rel in sorted(set(old_files) - files):
        ops.append({"op": "refused", "path": rel, "why": "deleted: nothing in this system deletes files"})
    ops += lists_last                                           # the invoice list goes up after its PDFs
    for op in list(ops):
        if op["op"] in ("upload", "create_sheet") and op["path"].split("/", 1)[0].startswith("coach-") \
                and ("/invoices/" in op["path"] or "/invoice-lists/" in op["path"]):
            ops.append({"op": "lock", "path": op["path"]})
    for op in ops:
        if "values" in op:
            op["values"] = as_written(op["values"])

    problems = [f"{o['path']}: {o['why']}" for o in ops if o["op"] == "refused"]
    for o in ops:
        if o["op"] in ("refused", "lock"):
            continue
        p = o["path"]
        if role == "coach":
            ok = (o["op"] == "upload" and p.startswith(f"{coach}/invoices/") and p.endswith(".pdf")
                  and p.rsplit("/", 1)[0] in old_dirs) or \
                 (o["op"] == "create_sheet" and p.startswith(f"{coach}/invoice-lists/"))
            if not ok:
                problems.append(f"{p}: a coach's Claude may only upload its PDFs into an existing month folder and "
                                f"create its invoice-list Sheets (not '{o['op']}')")
        elif role == "head-coach":
            top = p.split("/", 1)[0]
            if top.startswith("coach-") and not (o["op"] == "create_folder" or p.endswith(("/me", "/clients", "/unpaid"))
                                                 or (o["op"] == "create_doc" and p.endswith("README"))
                                                 or (o["op"] in ("create_sheet",) and p.endswith(("/clients", "/unpaid")))):
                problems.append(f"{p}: the head coach's Claude doesn't write a coach's invoices, lists or POPs "
                                f"(not '{o['op']}')")
    return ops, problems


def describe(op: dict) -> str:
    o = op["op"]
    if o == "create_folder":
        return f"create folder {op['path']}/"
    if o == "upload":
        return f"upload {op['path']} ({op['mime']}) into {op['folder']}/"
    if o == "create_sheet":
        extra = f", with a dropdown on '{op['dropdown']['column']}'" if op.get("dropdown") else ""
        return f"create Sheet {op['path']} in {op['folder']}/ ({len(op['values'])} rows{extra})"
    if o == "append":
        return f"append {len(op['values'])} row(s) to Sheet {op['path']}"
    if o == "rewrite":
        return f"clear and rewrite Sheet {op['path']} ({len(op['values'])} rows)"
    if o in ("create_doc", "replace_doc"):
        return f"{'create' if o == 'create_doc' else 'replace the text of'} Doc {op['path']}"
    if o == "lock":
        return f"lock {op['path']} read-only"
    return f"REFUSED {op['path']}: {op.get('why', '')}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("work")
    p = sub.add_parser("plan"); p.add_argument("work"); p.add_argument("--role", choices=["coach", "head-coach"], required=True)
    p.add_argument("--coach", default=""); p.add_argument("--json", action="store_true")
    a = ap.parse_args()
    work = Path(a.work)
    if a.cmd == "snapshot":
        snapshot(work)
        return
    if a.role == "coach" and not a.coach:
        ap.error("--coach coach-<slug> is needed for a coach")
    ops, problems = plan(work, a.role, a.coach)
    if problems:
        print("Refused — don't write anything to the drive:")
        for pr in problems:
            print("  " + pr)
        sys.exit(1)
    if a.json:
        print(json.dumps(ops, indent=1))
    else:
        print("Carry these out in this order, then re-read each one to check:" if ops else "Nothing to write.")
        for i, op in enumerate(ops, 1):
            print(f"  {i}. {describe(op)}")


if __name__ == "__main__":
    main()
