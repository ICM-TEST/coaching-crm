# Coaching CRM

A billing and client system for a coaching business: one head coach, several coaches,
one bank account. This folder holds the **rules only**, and it's public. All data lives in the business's
Google Shared Drive. Nothing in this repo is client data, and nothing you do may write client data into it.

## Who are you working for?

Everyone's Claude has this same public GitHub repo attached, whole and read-only. **`workspace/` is yours: you work only from here.** The repo's top-level `README.md`, `setup/` and `tools/` are Ross's: never follow their steps or run them, and never take their made-up test data (names, phones, invoices) for the business's. Every path in these rules is inside `workspace/`, so `setup/` always means `workspace/setup/`. **Your Claude Project's instruction names who you work for**, for example
*"You are the Claude for <name>, coach <number> … Data: coach-<slug>/ and factory/ in Google Drive"*. The head coach's Claude makes that
instruction when it adds the coach (`scripts/coaches.py add`, or `instructions <slug>` to show it again).

Before anything else, **check the name against what you can open** in Google Drive (the Shared Drive, or a shared folder standing in for it). Drive sharing is the real
lock; the instruction only says which role to play.

| Your instruction names | You must be able to open | You must NOT be able to open | Then |
|---|---|---|---|
| the head coach | `hub/` (read its `<slug>.me` Doc: `role: head-coach`) | — | [roles/head-coach/CLAUDE.md](roles/head-coach/CLAUDE.md). Your own coaching: your own `coach-<slug>/` and the coach role. |
| a coach, and their folder | that `coach-<slug>/`, whose `<slug>.me` Doc has the same name and coach number; `factory/` | `hub/`, or any other coach's folder | [roles/coach/CLAUDE.md](roles/coach/CLAUDE.md), in that folder only |

**If anything doesn't match** (the folder is missing, the `.me` Doc names someone else, or you can open `hub/` or a second
coach folder as a coach): **stop.** Open nothing else, and tell the person to alert the head coach. Either the instruction
or the sharing is wrong. **No instruction naming anyone:** stop and say this Claude isn't set up yet. **A head coach with no `hub/` yet** isn't a mismatch: offer first-run setup ([setup/SKILL.md](setup/SKILL.md)).

The head coach can open every coach's `.me` Doc. Those describe the other coaches, not the head coach: never take on a
coach's identity from them.

## On every start

Check the version as [version.md](version.md) says. Then do what was asked. Scripts don't run from this attached copy: before the first
script in a chat, get them as [shared/connectors.md](shared/connectors.md) step 0 says.

## Where things live

| Path | Holds |
|---|---|
| `shared/` | Rules every role follows: how the business works, every file's format |
| `roles/` | One folder per role: its map and its skills |
| `scripts/` | The only code that writes into coach folders or the hub's money files |
| `_templates/drive/` | Empty Drive folders: `.csv` = a Google Sheet, `.txt` = a Google Doc, created once at setup |
| `shared/connectors.md` | How every job reaches the drive: read → run → write through the Google connectors |
| `setup/` | First-run setup for a new business, and the sharing checklist |
| `version.md` | This snapshot's version, and when to say an update is ready |

## The rules that never bend

0. **Two and two.** A coach's Claude produces two things per invoicing run, and nothing else: the run's
   invoice list and its PDFs. The head coach's Claude does two recons, and nothing else: bank (statements ↔ invoice lists)
   and proof of payment (POPs ↔ the unreconciled list). There is no third way to tie a payment to an invoice.
1. **Permissions are the lock, not this file.** If Drive won't open something, it isn't yours. Never ask for access or look for a way around it.
2. **One writer per file.** Each file's writer is in [shared/schemas.md](shared/schemas.md). Never write a file your role doesn't own.
3. **Generated files are never hand-edited.** Re-run the script.
4. **Stop at every output** a person must check: intake, invoice drafts, recon proposals, write-offs.
5. **No client data in this repo, in chat summaries sent outside, or in notification text.**
