# Skill — who's done a month

**Nobody opens a month.** Each coach's Claude makes its own month folder when it issues, and a coach is done when their
invoice list for the month exists. Invoices are due on `invoice_day` in `factory/business`. The month-end recon waits
until every active coach is done; it checks this itself.

## "Who's done November?" (or "open November invoicing")
1. `python3 scripts/runs.py --root <drive> status 2026-11`
2. Report it as printed: done (with invoice count and total), not done. If they asked to open a month, say there's
   nothing to open: coaches invoice on their own.
