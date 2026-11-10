# coaching-crm

A billing and client system for a coaching business, run as an ICM workspace: one head coach, several coaches, one bank
account. This repo holds the **structure**. Each business's **data** lives in its own Google Shared Drive.

> **No client data ever lives in this repo. It's public.** If you see a real name, phone number or bank detail in a commit,
> treat it as a leak.

**Claude:** start at [workspace/CLAUDE.md](workspace/CLAUDE.md). Everything outside `workspace/` is Ross's.

## Two roots

| Root | Where | Who reads it | Who changes it |
|---|---|---|---|
| **Structure** | This repo, public. Its `workspace/` folder is attached to each person's Claude Project as knowledge; jobs download the rest | Each person's Claude, and anyone else, so it never holds client data | Only Ross |
| **Data** | The business's Google Shared Drive, shared folder by folder | Each person's Claude, limited by Drive sharing | Each role, through the scripts |

## Layout

| Folder | What | Who uses it |
|---|---|---|
| `workspace/` | Rules and skills, markdown only. **The only folder attached to a Project.** Agents start at [workspace/CLAUDE.md](workspace/CLAUDE.md) | Everyone's Claude |
| `scripts/` | The code every job runs, downloaded by each job | Everyone's Claude, in its sandbox |
| `_templates/` | The empty Drive folders and the invoice fonts | Setup and the invoice generator |
| `setup/` | Ross's onboarding and questionnaire | Ross only |
| `tools/` | Ross's tests, release and font tools | Ross only |

Only `workspace/` is attached to a Project. Attaching the rest adds about 230 KB of code and tests to every chat for nothing.

## Changing the live system

1. Edit, commit.
2. `python3 tools/release.py --note "what changed"` scans for personal data, runs the tests, bumps the version, commits,
   tags `vX.Y.Z` and pushes. Jobs download their scripts from that tag, so rules and code never drift apart.
3. Tell the head coach to say "version <x> is out" to their Claude. Each person's Claude then says an update is ready until they press
   Sync, which is desktop only. Until then they run the previous version.

## Tests

`python3 tools/tests/test_cycle.py` and `test_coaches.py` need only Python 3.10+. `test_setup.py`, `test_release.py`, `test_statements.py`, `test_clients.py` and `test_usage.py` too. `test_issue.py`, `test_sync.py` and `test_updates.py` also need reportlab.

## Status

| Piece | State |
|---|---|
| Role maps and skills (head coach, coach) | drafted |
| First-run setup (`workspace/setup/SKILL.md`) | written, plan rehearsed; not yet run in claude.ai |
| `issue.py`: the invoice generator (a coach's two outputs) | built, tested; one fixed layout for every coach, in Inter (included, trimmed, SIL OFL); ~40 KB per PDF; needs reportlab |
| Drive templates: `.csv` = Google Sheet, `.txt` = Google Doc | drafted |
| `sync.py`: working-copy changes → Google connector steps, with each role's limits | built, tested |
| The head coach's `all-invoices` copy of every sealed invoice | built, tested |
| `coaches.py`: the list of coaches (add with next coach number, list, leave: their clients become unallocated) and the step-by-step share, welcome and unshare texts | built, tested; the texts' claude.ai and Drive button names not yet checked |
| `clients.py`: the head coach's own client details, and importing an existing client list | built, tested |
| `build_lists.py`: each coach's `<slug>.me` Doc and client list, books | built, tested |
| `runs.py`: who's done a month (nobody opens one); the month-end gate | built, tested |
| `recon.py`: bank recon (any bank's statements, CSV or PDF, read into one layout and balance-checked), POP recon, unreconciled live list, overpayments, write-off | built, tested on made-up data; PDF statements not yet tried in claude.ai |
| The client form: built by the head coach from Claude's steps, answers in `hub/client-form responses`; intake reads them | skills written |
| `check_sharing.py` | **not built** |
| Credits, refunds, year-end reports | **out of scope for this build** (handled in the head coach's own accounting system) |

No client data belongs in this repo, ever.
