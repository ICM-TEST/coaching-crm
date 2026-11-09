"""Shared helpers: Sheets as CSV, Docs as `key: value` text, money, and the Drive tree's paths.

The data lives in Google Sheets and Docs. Claude reads them through the connectors into a working copy, where each
Sheet is a `.csv` and each Doc a `.txt` (same folders, same names), and the scripts work on that copy. scripts/sync.py
then turns the changes back into connector steps.

A Sheet may start with a short preamble (title and note rows starting `#`, `key:` / value rows, blank rows); the
first other row is the table's header. A generated Sheet can hold several tables, each after a `## Heading` row.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import os
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


# ---------- money and dates ----------

def money(value) -> Decimal:
    """Tolerant of how a Sheet or a statement may write a number: 1,440.00, 1440, 1 440.00, a currency symbol or code
    in front, or (85.00) for money out."""
    if value is None or str(value).strip() == "":
        return ZERO
    raw = str(value).strip()
    text = re.sub(r"[^\d.\-]", "", raw)
    if raw.startswith("(") and raw.endswith(")") and not text.startswith("-"):
        text = "-" + text
    return Decimal(text).quantize(CENT, rounding=ROUND_HALF_UP)


def is_placeholder(value) -> bool:
    """A template value nobody has filled in yet: <like this>."""
    v = str(value or "").strip()
    return v.startswith("<") and v.endswith(">")


def fmt(amount: Decimal) -> str:
    return f"{amount.quantize(CENT):.2f}"


def today() -> str:
    """Today, or CRM_TODAY when tests pin the date."""
    return os.environ.get("CRM_TODAY") or dt.date.today().isoformat()


def iso_date(value: str) -> str:
    """YYYY-MM-DD, also from the forms a Sheet may show, depending on its locale (24/10/2026, 2026/10/24)."""
    v = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(v, pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"not a date: {value!r}")


def days_between(earlier: str, later: str) -> int:
    return (dt.date.fromisoformat(iso_date(later)) - dt.date.fromisoformat(iso_date(earlier))).days


# ---------- Sheets (CSV in the working copy) ----------

def _rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    return list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))


def _preamble(row: list[str]) -> bool:
    first = (row[0] if row else "").strip()
    return not any(c.strip() for c in row) or first.startswith("#") or first.endswith(":")


def read_sheet(path: Path) -> tuple[dict, list[dict]]:
    """(preamble values, rows of the first table). Blank rows inside the table are skipped."""
    rows, meta, i = _rows(path), {}, 0
    while i < len(rows) and _preamble(rows[i]):
        r = rows[i]
        if r and r[0].strip().endswith(":") and not r[0].strip().startswith("#"):
            meta[r[0].strip()[:-1].strip()] = (r[1] if len(r) > 1 else "").strip()
        i += 1
    if i >= len(rows):
        return meta, []
    header = [h.strip() for h in rows[i]]
    while header and not header[-1]:
        header.pop()
    out = []
    for r in rows[i + 1:]:
        if not any(c.strip() for c in r) or r[0].strip().startswith("# "):
            continue
        if r[0].strip().startswith("## "):
            break                                           # the next table in a generated Sheet
        r = r + [""] * (len(header) - len(r))
        out.append({h: r[k].strip() for k, h in enumerate(header)})
    return meta, out


def read_table(path: Path) -> list[dict]:
    return read_sheet(path)[1]


def read_sections(path: Path) -> dict[str, list[dict]]:
    """A generated Sheet's tables by heading (for people and tests; the scripts never read generated Sheets back)."""
    out, current, header = {}, None, None
    for r in _rows(path):
        first = (r[0] if r else "").strip()
        if first.startswith("## "):
            current, header = first[3:].strip(), None
            out[current] = []
        elif current is not None and any(c.strip() for c in r) and not first.startswith("# "):
            if header is None:
                header = [h.strip() for h in r]
            else:
                out[current].append({h: (r[k] if k < len(r) else "").strip() for k, h in enumerate(header)})
    return out


def _clean(value) -> str:
    return str(value if value is not None else "").replace("\n", " ").strip()


def _csv(rows: list[list]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([[_clean(c) for c in r] for r in rows])
    return buf.getvalue()


def write_sheet(path: Path, columns: list[str], rows: list[dict], meta: dict | None = None,
                title: str = "", notes: list[str] = ()) -> None:
    """Write a whole Sheet: optional title and notes, `key:` / value rows, a blank row, then the table."""
    lines: list[list] = []
    if title:
        lines.append([f"# {title}"])
    lines += [[f"# {n}"] for n in notes]
    lines += [[f"{k}:", v] for k, v in (meta or {}).items()]
    if lines:
        lines.append([])
    lines.append(columns)
    lines += [[r.get(c, "") for c in columns] for r in rows]
    path.write_text(_csv(lines), encoding="utf-8")


def append_rows(path: Path, columns: list[str], rows: list[dict]) -> None:
    """Add rows at the end of a Sheet (appended on the drive with the Sheets connector's append)."""
    if not rows:
        return
    text = path.read_text(encoding="utf-8") if path.exists() else _csv([columns])
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + _csv([[r.get(c, "") for c in columns] for r in rows]), encoding="utf-8")


def _split(path: Path) -> tuple[list[list[str]], list[list[str]]]:
    rows = _rows(path)
    i = 0
    while i < len(rows) and _preamble(rows[i]):
        i += 1
    return rows[:i], rows[i:]


def rewrite_table(path: Path, columns: list[str], rows: list[dict]) -> None:
    """Replace a Sheet's table, keeping its title, notes and `key:` rows."""
    pre, _ = _split(path)
    path.write_text(_csv(pre + [columns] + [[r.get(c, "") for c in columns] for r in rows]), encoding="utf-8")


def set_sheet_meta(path: Path, key: str, value: str) -> None:
    """Set one `key:` / value row in a Sheet's preamble (adding it if missing)."""
    pre, table = _split(path)
    for r in pre:
        if r and r[0].strip() == f"{key}:":
            r[1:] = [value]
            break
    else:
        at = next((i for i in range(len(pre) - 1, -1, -1) if pre[i] and pre[i][0].strip().endswith(":")), len(pre) - 1)
        pre.insert(at + 1 if pre else 0, [f"{key}:", value])
    path.write_text(_csv(pre + table), encoding="utf-8")


def write_generated(path: Path, title: str, intro: str, sections: list[tuple[str, list[str], list[dict]]]) -> bool:
    """Write a generated Sheet (rebuilt, never edited). Returns True if its content changed (ignoring the date line)."""
    lines: list[list] = [[f"# {title}"], [f"# Generated {today()}. Don't edit: rebuilt at each recon."]]
    lines += [[f"# {line}"] for line in intro.split("\n") if line.strip()]
    for heading, columns, rows in sections:
        lines += [[], [f"## {heading}"]]
        lines += [columns] + [[r.get(c, "") for c in columns] for r in rows] if rows else [["# None."]]
    new = _csv(lines)
    old = path.read_text(encoding="utf-8") if path.exists() else ""

    def body(t: str) -> str:
        return "\n".join(l for l in t.splitlines() if not l.startswith("# Generated "))

    if body(old) != body(new) or not path.exists():
        path.write_text(new, encoding="utf-8")
    return body(old) != body(new)


# ---------- Docs (`key: value` text in the working copy) ----------

def frontmatter(path: Path) -> dict:
    """The `key: value` lines of a Doc (headings, notes and other lines are ignored)."""
    if not path.exists():
        return {}
    data = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$", line)
        if m:
            data[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return data


def set_frontmatter(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if re.match(rf"^\s*{re.escape(key)}\s*:", line):
            lines[i] = f"{key}: {value}"
            break
    else:
        lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- the Drive tree ----------

class Drive:
    """Paths inside the business's Shared Drive, or a working copy of it (shared/schemas.md)."""

    def __init__(self, root):
        self.root = Path(root).expanduser()
        self.hub = self.root / "hub"
        self.factory = self.root / "factory"
        if not self.hub.is_dir():
            raise SystemExit(f"No hub/ under {self.root}. Is --root the Shared Drive (or its working copy), and is this "
                             "the head coach's account?")

    def coach_dir(self, slug: str) -> Path:
        return self.root / f"coach-{slug}"

    def coaches(self, active_only: bool = True) -> list[dict]:
        rows = read_table(self.hub / "coaches.csv")
        if active_only:
            rows = [r for r in rows if r.get("active", "").lower() in ("yes", "true", "y", "1")]
        return rows

    def all_coach_slugs(self) -> list[str]:
        """Every coach who has ever had a folder: invoices outlive active status."""
        return [r["slug"] for r in self.coaches(active_only=False) if self.coach_dir(r["slug"]).is_dir()]
