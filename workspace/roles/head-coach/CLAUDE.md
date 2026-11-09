# Head coach

You work for the head coach. You can open `hub/`, `factory/` and every `coach-<slug>/` folder.
That reach is why every write into a coach folder goes through `scripts/`, never by hand:
the scripts filter by coach, and you don't.

**The head coach does two recons, and only two:** bank (statements ↔ invoice lists) and proof of payment
(POPs ↔ the unreconciled live list). See [skills/recon.md](skills/recon.md).

## On every start

Read `hub/coaches`, `hub/clients` and `factory/client-form`. Say first, in one line each, only what applies:
- Setup isn't finished: no coach but the head coach, no `link:` in `factory/client-form`, or no clients in
  `hub/clients`. Name the next step from first-run setup's *Finish* ([../../setup/SKILL.md](../../setup/SKILL.md)), and
  offer to start it.
- Clients waiting for a coach: *"<n> clients are unallocated and need a coach."* Offer to assign them.

**Do not load:** `roles/coach/` (unless the head coach is doing their own coaching, below), or coaches' PDFs.
Recon needs only their `invoice-lists/`, and the scripts read those.

## Route by what the head coach says

| They say | Skill | Stop for them at |
|---|---|---|
| "set up my workspace" (no `hub/` yet) | [../../setup/SKILL.md](../../setup/SKILL.md) | before anything is written |
| "add a client <details>" | [skills/assign.md](skills/assign.md) → *Add one by hand* | confirm the details and coach |
| "add a coach" / "<coach> is leaving" | [skills/coaches.md](skills/coaches.md) | the details read back, before anything is written |
| "list the coaches" | `scripts/coaches.py list` | — |
| "what do we keep about clients?" / "set up my client form" / "bring in my clients" | [skills/client-setup.md](skills/client-setup.md) | each part's read-back |
| "list the clients" | read `hub/clients` (by coach: `scripts/coaches.py list` gives the counts) | — |
| "check intake" / new form responses | [skills/intake.md](skills/intake.md) | the intake proposal |
| "assign / move <client> to <coach>" | [skills/assign.md](skills/assign.md) | before rebuilding lists if anything is ambiguous |
| "open <month> invoicing" / "who's done <month>?" | [skills/invoicing-run.md](skills/invoicing-run.md) | — |
| "run recon" (bank statement) | [skills/recon.md](skills/recon.md) → Recon 1 | the bank proposal |
| a POP arrives / "do the POP recon" | [skills/recon.md](skills/recon.md) → Recon 2 | the POP proposal |
| "push" (after deciding a proposal) | [skills/recon.md](skills/recon.md) → Push | — |
| "version <x> is out" (from Ross) | set `version:` in `factory/release` through the Docs connector | — |
| "what's unreconciled?" | read `hub/unreconciled` | — |
| "write off <invoice>" | [skills/recon.md](skills/recon.md) → Write-offs | confirm the amount before recording |
| "what's outstanding?" / "who hasn't paid?" | read `hub/summary`: unpaid invoices across every coach, longest unpaid first | — |
| overpayments / credits / refunds | read `hub/summary` → Overpayments. Handled in the head coach's own accounting system, not here. | — |
| their own invoicing, unpaid | switch to [../coach/CLAUDE.md](../coach/CLAUDE.md) **inside `coach-<their slug>/` only** | as that role says |

## Scripts

Every job is read → run → write ([../../shared/connectors.md](../../shared/connectors.md)): download what it needs into
`work/`, snapshot, run with `--root work`, then carry out `sync.py plan work --role head-coach`.

| Script | Does |
|---|---|
| `scripts/sync.py snapshot\|plan` | read → run → write through the connectors ([../../shared/connectors.md](../../shared/connectors.md)) |
| `scripts/coaches.py add\|list\|leave\|share\|welcome\|unshare` | the list of coaches, and the step-by-step texts for sharing, a coach's setup and removing access |
| `scripts/clients.py details\|import` | the details kept about each client, and bringing in an existing list |
| `scripts/build_lists.py coach-clients` | list of coaches + list of clients → each coach's `<slug>.me` and `clients` |
| `scripts/runs.py open\|status` | open a run; who's done |
| `scripts/recon.py bank\|pops\|push` | the two recons |
| `scripts/recon.py write-off` | record a write-off the head coach agreed with a coach (not a recon) |

## Notifying coaches

Leave a Drive comment on the coach's file that @-mentions them (Google emails them). The text names the file
and date only, for example *"@<coach> unpaid list updated <date>"*, never a client or an amount.
