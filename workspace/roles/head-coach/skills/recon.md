# Skill — the two recons

Every recon is read → run → write through the connectors: [../../../shared/connectors.md](../../../shared/connectors.md).
**Read** for a recon, in this order, and nothing more:
1. All of `hub/` (Sheets as CSV, Docs as text; bank statements and POPs aren't downloaded), plus `factory/business` and
   `factory/release`.
2. One folder listing per coach folder and one of `hub/bank/`, written to `.drive-index.csv` (`path`, `size`,
   `modified`). No file is opened for this.
3. `python3 scripts/recon.py --root work lists-needed`. It names the invoice lists to download: the new ones, and any
   changed since the head coach's copy was taken. **Download only those.** Every other list is already in
   `hub/all-invoices`, and the books work from that copy.

**Write**: `python3 scripts/sync.py plan work --role head-coach`, then carry it out. To **push**, download the
proposal Sheet again first, so the head coach's dropdown choices are in the working copy.

**Hard rule: the head coach does two recons, and only two.** There is no other way to tie a payment to
an invoice: no matching by hand, no editing allocations, no "just this one". If the head coach asks for
something that is neither recon, say which recon it belongs in.

| Recon | Reconciles | Against | Leaves behind |
|---|---|---|---|
| **1. Bank** | the bank statements (money in only) | the coaches' invoice lists | the **unreconciled live list**: client money it couldn't place |
| **2. Proof of payment** | the POPs coaches upload to `coach-<slug>/pops/` (and any in `hub/pops/`) | **the unreconciled live list only** | POPs still waiting (money not in the bank yet) |

Both work the same way: **propose → the head coach decides every `?` → push.**

---

## Recon 1 — bank: "run recon"

### Read new statements
The head coach uploads each statement to `hub/bank/` exactly as the bank gives it: a CSV export or a PDF, from any bank.
A statement with no Sheet of the same name in `hub/bank/lines/` is new. After the snapshot (so the write step creates
its Sheet), for each new one:

1. Read it through the Drive connector.
2. Work out its layout from the statement itself: where each line's date, description, amount (or separate money-in
   and money-out columns) and balance are; how dates are written (a day over 12 tells day-first from month-first); how
   money out is shown (a minus, brackets, its own column). Never assume a bank, country or format the statement doesn't show.
3. Write `work/hub/bank/lines/<statement file name>.csv` with the columns `date,description,amount,balance`
   ([../../../shared/schemas.md](../../../shared/schemas.md)): one row per transaction, in the statement's order, nothing
   left out. Dates as YYYY-MM-DD, amounts as plain numbers (money in `1400.00`, money out `-85.00`), the balance as
   printed, or blank if there's none. For a CSV, put the export in your sandbox (outside `work/`) and convert it with a
   short script, never by retyping. For a PDF, write the rows from its text.
4. If a file isn't a bank statement, or can't be read, stop and tell the head coach.

The recon checks each statement line by line against its running balance. If it says a balance doesn't follow, read that
part of the statement again and fix the lines. If it still fails, show the head coach the lines around it, and add
`--skip-balance-check` only if they've compared the statement's totals and say go ahead. For a statement with no balance,
give the head coach the money-in total the recon prints, and ask them to compare it with the statement.

### Propose
1. Month end? Use `--month-end <period>`. Follow-up? Leave it off.
   `python3 scripts/recon.py --root <drive> bank --month-end 2026-11`
2. If it prints **GATE: not complete**, tell the head coach who's outstanding and stop. Only add `--force`
   if they say "run anyway", and tell them whose payments will wait.
3. Open the proposal (`hub/recon/bank-YYYY-MM-DD`). Give the head coach the summary at the top (with what was read
   from each new statement), then **only** the `?` rows, one by one, with the options in `note`.

### Human check — STOP
**Every payment the recon couldn't place gets a `?`**, so nothing unknown slips through. The head coach picks each
decision from the dropdown in the proposal Sheet (or tells you, and you set it through the Sheets connector):
- accept as proposed → `accept`
- a different invoice → change `coach`, `client_id`, `invoice`, `amount`, then `accept`
- client money, but they can't say whose → `unreconciled` (it goes on the live list for the POP recon)
- not client money (transfers, supplier refunds, own deposits) → `non-client`
- not sure yet → `hold` (asked again at the next bank recon)

Never change a row they didn't decide. Never set `accept` on your own judgment.
Payments already on the live list are re-checked against new invoice lists at every bank recon (a prepayment
whose invoice now exists, for example). They only appear when something new fits, so nobody is asked twice.

### Push
1. `python3 scripts/recon.py --root <drive> push hub/recon/bank-YYYY-MM-DD`. It refuses while any `?` remains.
2. Tell the head coach the totals in `hub/summary` and the size of the live list in `hub/unreconciled`.
3. **Folder checks** (top of every proposal, and in `hub/summary`): anything in a coach's folder the system didn't make,
   or that changed since, e.g. a list edited in a Claude chat outside the coach's Project. A changed or unsealed list is
   left out of the books until it's sorted out: restore it from the file's Drive version history, or have the coach
   re-issue through their Project. Stray files get removed. Tell the head coach about each one.

---

## Recon 2 — proof of payment: "do the POP recon"

A client being chased says they've already paid. The coach gets a POP and uploads it to their own `coach-<slug>/pops/`.
POPs that reach the head coach directly go in `hub/pops/`. The bank recon's summary says how many are waiting.

### Read the POPs
For every POP file (in any `coach-<slug>/pops/` or `hub/pops/`) that isn't in `hub/pop-register`, read it and append one
row: `file` (its path from the drive root, e.g. `coach-<slug>/pops/<invoice number> <client name>.pdf`) · today · payment date · amount · payer name · reference · and the `client`/`invoice` **if the coach said**
what it's for. Copy what the POP shows. Don't guess.

### Propose
`python3 scripts/recon.py --root <drive> pops` writes `hub/recon/pop-YYYY-MM-DD`. For each unused POP it looks for the
payment **on the live list only** (same amount, within a week), then the invoice (the one the coach named, else by
name or reference). **A POP a coach uploaded is only matched to that coach's invoices**, and push refuses anything else.
- `accept`: payment and invoice found.
- `?`: payment found, invoice unclear. The head coach picks it.
- `hold`: no payment on the live list fits. The money hasn't cleared, went to another account, or arrived after
  the last bank recon. **Run the bank recon first**, then try again. Nothing is recorded, and the POP waits.

### Human check — STOP
Read the head coach each match: *"<client>'s POP, <amount> on <date> → the live-list payment '<bank description>' →
<invoice number> (<coach>)."* Decisions: `accept` or `hold` only.

### Push
`python3 scripts/recon.py --root <drive> push hub/recon/pop-YYYY-MM-DD`. It refuses any row whose payment isn't on
the live list, and any POP used twice. The payment leaves the live list, the invoice leaves the coach's unpaid list,
and nothing else changes in the coach's folder.

---

## Not a recon: write-offs

A write-off is a record of what the head coach agreed directly with a coach. Coaches don't write it anywhere.

1. Repeat it back with the figures from the coach's `unpaid`, and **wait for a yes**:
   *"Write off <invoice number>, <client>, balance <amount>, for <coach>, reason '<reason>'. Record it?"*
2. Then:
   `python3 scripts/recon.py --root <drive> write-off <invoice number> --reason "<reason>"`
3. The command refuses amounts above the invoice balance, and rebuilds the coach's files.

## Overpayments

When a payment is more than the invoice, the recon pays the invoice in full and records the excess as an
**overpayment**. It's listed on `hub/summary` for the head coach to deal with in their own accounting system
(credit the client, or refund). This system keeps no credits, and coaches don't see overpayments.
