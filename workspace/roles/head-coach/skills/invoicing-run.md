# Skill — invoicing run

A run is one month's invoicing. Each coach's run produces exactly two things: an invoice list in their
`invoice-lists/` and the PDFs. **A coach is done when their list for the period exists.** The month-end
recon waits until every active coach is done.

## Open a run — "open November invoicing"
Invoices go out on `invoice_day` in `factory/business` (the 24th), and the run is due that day.
1. `python3 scripts/runs.py --root <drive> open 2026-11` (add `--due 2026-11-25` only if the head coach names another day).
   It also makes `invoices/2026-11/` in every active coach's folder: coaches' Claudes never make folders.
2. Leave one Drive comment on `factory/invoicing-runs` @-mentioning every active coach:
   *"November invoicing is open, due 24 Nov."*

## Check a run — "who's done November?"
1. `python3 scripts/runs.py --root <drive> status 2026-11`
2. Report it as printed: done (with invoice count and total, from each coach's list), not done.
3. Offer to remind the coaches who aren't done: one Drive comment on `factory/invoicing-runs` tagging only them.

## Close
`runs.py status` prints `COMPLETE` when every active coach has a list for the period. The month-end recon checks this itself.
