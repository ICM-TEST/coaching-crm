# shared/ — how the business works

The rules both roles follow. Formats for every file: [schemas.md](schemas.md). Lists are Google Sheets, other data
files Google Docs, reached through the Google connectors: [connectors.md](connectors.md).

## The money flow

1. Clients join through **one Google Form** owned by the head coach. Coaches hand out the fill-in link only.
2. The head coach keeps the **main client list** and assigns each client to a coach.
3. **Nobody opens a month.** Each coach invoices on their own; invoices go out on the business's **invoice day** (`invoice_day`
   in `factory/business`, set at first-run setup) and are **due immediately**.
4. Each coach keeps track of their lessons **their own way**. At the run, they invoice for work actually done.
   No one approves invoices. What's billable (no-shows, late cancellations) is each coach's own policy.
   **Once issued, an invoice is due** until it's paid or written off. While it's unpaid, the coach can update it through the generator.
5. **A coach's run produces exactly two outputs:** the run's **invoice list** (which the head coach's recon reads)
   and the **PDF invoices** (which the coach sends to clients). Nothing else. Both are made only by the invoice
   generator inside the coach's Claude Project; it seals them, and the recon ignores and reports anything else.
6. Every invoice pays into **the business bank account** (from `factory/`, never typed by a coach).
7. **The head coach does two recons, and only two:**
   - **Bank recon:** the bank statements (CSV or PDF) against the coaches' invoice lists. The month-end one waits until every coach's
     list for the month exists; follow-ups can run any time. Every payment it can't place is **verified by the head
     coach**: client money or not. Non-client money drops out. Client money it can't tie to an invoice goes on the
     **unreconciled live list**, which carries over from recon to recon.
   - **POP recon:** the proofs of payment coaches upload to their `pops/` folders (plus any in `hub/pops/`) against the
     unreconciled live list, and nothing else.
8. There is no third way to tie a payment to an invoice.
9. Each coach receives **only their own** unpaid list, and chases their own clients. **About money, a coach sees only
   which invoices are unpaid, and for how long.** No payment dates, amounts received, bank lines, overpayments or how
   a payment was matched. The head coach sees the same unpaid list across every coach.
10. A client who says they've already paid is asked for **proof of payment (POP)**. The coach uploads it to their own
    `pops/` folder; the head coach's POP recon picks it up. That clears the invoice from the coach's unpaid list.

## Lifecycle words

| Thing | Values |
|---|---|
| Client status | `new` (no coach yet) · `active` · `left` |
| EFT state | matched · `non-client` · unreconciled (the live list) · unreviewed |
| Allocation kind | `payment` · `overpayment` · `write-off` |

Clients are never deleted. A returning client reuses their row: `left → active`.

## Money rules

- **No credits in this system, for now.** An overpayment pays its invoice in full, and the excess is recorded as an
  `overpayment` on the head coach's summary. The head coach deals with it in their own accounting system (credit or refund).
  Coaches don't see overpayments.
- **Write-offs** are agreed directly between the coach and the head coach. Once the head coach confirms,
  their Claude records it, and the invoice leaves the coach's unpaid list. The invoice stays on record.
- **Moving a client** to another coach doesn't move their open invoices. Those stay with the coach who issued them.
- **Payouts** between the head coach and coaches are settled outside this system.

## Language

A coach's Claude makes invoices and invoice lists only. It doesn't write messages or reminders to clients;
coaches do that themselves.
