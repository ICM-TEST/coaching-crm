# coaching-crm

A billing and client system for a coaching business, run as an ICM workspace: one head coach, several coaches, one bank
account. This repo holds the **structure**. Each business's **data** lives in its own Google Shared Drive.

> **No client data ever lives in this repo. It's public.** If you see a real name, phone number or bank detail in a commit,
> treat it as a leak.

## Two roots

| Root | Where | Who reads it | Who changes it |
|---|---|---|---|
| **Structure** | `workspace/`, public, attached to each person's Claude Project as knowledge | Each person's Claude, and anyone else, so it never holds client data | Only Ross |
| **Data** | The business's Google Shared Drive, shared folder by folder | Each person's Claude, limited by Drive sharing | Each role, through the scripts |

## Layout

| Folder | What | Attached to Projects? |
|---|---|---|
| `workspace/` | Rules, skills, scripts and Drive templates. Agents start at [workspace/CLAUDE.md](workspace/CLAUDE.md) | **Yes**, the only folder attached |
| `setup/` | Ross's onboarding and questionnaire | No |
| `tools/` | Ross's tests, release and font tools | No |

## Changing the live system

1. Edit, commit.
2. `python3 tools/release.py --note "what changed"` runs the tests, scans for personal data, bumps the version, commits and pushes.
3. Tell the head coach's Claude "version <x> is out". Each person's Claude then says an update is ready until they press
   Sync, which is desktop only. Until then they run the previous version.

## Tests

`python3 tools/tests/test_cycle.py` and `test_coaches.py` need only Python 3.10+. `test_setup.py` and `test_release.py` too. `test_issue.py`, `test_sync.py` and `test_updates.py` also need reportlab.

## Status

| Piece | State |
|---|---|
| Role maps and skills (head coach, coach) | drafted |
| First-run setup (`workspace/setup/SKILL.md`) | written, plan rehearsed; not yet run in claude.ai |
| `issue.py`: the invoice generator (a coach's two outputs) | built, tested; matches the business's own invoice, in Inter (included, trimmed, SIL OFL); ~40 KB per PDF; needs reportlab |
| Drive templates: `.csv` = Google Sheet, `.txt` = Google Doc | drafted |
| `sync.py`: working-copy changes → Google connector steps, with each role's limits | built, tested |
| Morgan's `all-invoices` copy of every sealed invoice | built, tested |
| `coaches.py`: the list of coaches (add with next coach number, list, leave) | built, tested |
| `build_lists.py`: each coach's `me` and client list, books | built, tested |
| `runs.py`: invoicing run gate | built, tested |
| `recon.py`: bank recon, POP recon, unreconciled live list, overpayments, write-off | built, tested on made-up data |
| Intake from the Google Form | skill written; reads the Sheet through the connector |
| `check_sharing.py` | **not built** |
| Credits, refunds, year-end reports | **out of scope for this build** (handled in the head coach's own accounting system) |

No client data belongs in this repo, ever.
