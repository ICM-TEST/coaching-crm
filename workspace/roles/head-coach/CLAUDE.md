# Head coach

You work for the head coach. You can open `hub/`, `factory/` and every `coach-<slug>/` folder.
That reach is why every write into a coach folder goes through `scripts/`, never by hand:
the scripts filter by coach, and you don't.

**The head coach does two recons, and only two:** bank (CSV ↔ invoice lists) and proof of payment
(POPs ↔ the unreconciled live list). See [skills/recon.md](skills/recon.md).

**Do not load:** `roles/coach/` (unless the head coach is doing their own coaching, below), or coaches' PDFs.
Recon needs only their `invoice-lists/`, and the scripts read those.

## Route by what the head coach says

| They say | Skill | Stop for them at |
|---|---|---|
| "set up my workspace" (no `hub/` yet) | [../../setup/SKILL.md](../../setup/SKILL.md) | before anything is written |
| "add a client <details>" | [skills/assign.md](skills/assign.md) → *Add one by hand* | confirm the details and coach |
| "add a coach" / "list the coaches" / "<coach> is leaving" | `scripts/coaches.py add\|list\|leave`; then the sharing checklist. `add` creates and names the coach's folder and prints the Project instruction for their Claude: give it to the head coach to set up. | confirm name, phone, email, next invoice number before adding |
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
| `scripts/coaches.py add\|list\|leave` | the list of coaches: each new coach gets the next coach number |
| `scripts/build_lists.py coach-clients` | list of coaches + list of clients → each coach's `me` and `clients` |
| `scripts/runs.py open\|status` | open a run; who's done |
| `scripts/recon.py bank\|pops\|push` | the two recons |
| `scripts/recon.py write-off` | record a write-off the head coach agreed with a coach (not a recon) |

## Notifying coaches

Leave a Drive comment on the coach's file that @-mentions them (Google emails them). The text names the file
and date only, for example *"@Ben unpaid list updated 5 Dec"*, never a client or an amount.
