# tools: Ross only

Attached to every Project with the rest of the repo, but no Project's Claude runs anything here or takes its
made-up data as real ([../workspace/CLAUDE.md](../workspace/CLAUDE.md) says so).

| Tool | Job |
|---|---|
| `tests/` | Made-up 8-coach data. Run before any change ships |
| `release.py` | Tests, personal-data scan, version bump, commit, push. `--dry-run`, `--scan-only` |
| `trim_fonts.py` | Trims the Inter fonts for small invoices |
