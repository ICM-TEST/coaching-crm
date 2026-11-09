# Skill — invoicing run

One run = two outputs: the invoice list and the PDFs. Format: [../../../shared/schemas.md](../../../shared/schemas.md) → *The invoice list*.

## Inputs
- **What the coach did this month, from their own records.** The system holds no lesson log. Take it in any form:
  a list they type or paste, an export from the app they use, a photo of their diary.
- `clients` (names → `client_id`), `factory/billable-work` (rates), `factory/business`

## Draft — "do my October invoices"
1. Turn the coach's records into lines per client: **one line per item per month**, with a quantity, e.g.
   *<item>, November, 4* and *<item>, October, 2*. Items come only from `factory/billable-work`.
   Its `billed` column says when each item is billed: **`in advance`** items can include next month's sessions on this
   run; **`after`** items cover only the month past. The generator refuses a line that breaks it.
2. For no-shows and late cancellations, ask once per case: bill it or not? It's their policy.
3. A name that isn't in `clients`: don't invent an id. Say the client isn't on their list yet; the head coach
   adds clients from the Form. The invoice prints the client's **full name and phone from `clients`**.
4. Ask who pays, if it's not the client (a parent, for example). That name goes in `payer`. It isn't printed, but
   recon needs it to recognise the payment.
5. One invoice per client. No credits are applied here: overpayments are the head coach's to handle.
6. Write the drafts as JSON **outside the drive** (see the top of `scripts/issue.py`) and do a dry run:
   `python3 scripts/issue.py --root <drive> --coach-dir coach-<slug> --period 2026-10 --drafts drafts.json --dry-run`
   It shows the exact invoice numbers (`2026-03-490`…: year-coach number-invoice number), lines and totals, or refuses
   with the reasons.
7. Show the coach that summary.

## Human check — STOP
The coach corrects or approves the drafts.

## Issue — "issue them"
`python3 scripts/issue.py --root <drive> --coach-dir coach-<slug> --period 2026-10 --drafts drafts.json`
- It makes every PDF in `invoices/<period>/` (`Invoice 2026-03-490.pdf`, …), **then** writes `invoice-lists/<month>`.
  Those are this coach's two outputs, and nothing else is written.
- Every invoice is the business's own layout ([factory/invoice-rules](../../../factory/invoice-rules) in the drive);
  only this coach's phone and email (from `me`) are theirs.
- The list existing is what tells the head coach this coach's run is done. **Nothing to bill?** Issue with
  `{"invoices": []}`, so the run still shows as done.
- The coach sends each PDF to its client themselves. You never send, and you don't write messages.

## Through the connectors (how every coach works: anywhere, a phone included)

Follow [../../../shared/connectors.md](../../../shared/connectors.md): read → run → write.

1. **Read.** `python3 scripts/issue.py --coach-dir coach-<slug> --needs` lists what to download into `work/`: this
   coach's `me` Doc and `clients` Sheet, their `invoice-lists` Sheets, the business Doc, the price list and run Sheets,
   the fonts (copied from the downloaded repo), and the month's PDF folder (check it exists; make the same empty folder in `work/`).
   Then `python3 scripts/sync.py snapshot work`.
2. **Draft, dry run, issue** as above, with `--root work`.
3. **Write.** `python3 scripts/sync.py plan work --role coach --coach coach-<slug>`. It lists: upload each PDF, create
   the invoice-list Sheet (**after** the PDFs), lock them all. Carry it out in that order, then list both folders on the
   drive to check every file is there.
   - The month's PDF folder and `invoice-lists/` **already exist**: the head coach's Claude makes every folder. **Never
     create, rename, move or delete anything on the drive.** If a folder is missing, stop and tell the coach to ask the
     head coach.
   - If the plan says **Refused**, write nothing and tell the coach why.

## Corrections
Never edit an issued list or PDF, and never make or change a PDF by hand: the head coach's recon would still use the old
amount. There are no credit notes.

**The client hasn't paid (lessons cancelled, say): update the invoice.** Download `unpaid` as well, and use the invoice's own
period. Give the lines the invoice should now have:
`{"updates": [{"invoice": "2026-03-490", "lines": [{"code": "PVT", "month": "2026-10", "qty": 2}]}]}`
For a whole invoice cancelled: `{"invoice": "2026-03-490", "cancel": true, "lines": []}`. Do the dry run and stop for the coach,
as for any invoice. It keeps its number and date, so the client pays with the same reference. The generator makes
`Invoice 2026-03-490 (updated).pdf` and a new sealed list. Upload them the same way; the plan lists the steps. The coach
sends the new PDF. The original stays in the folder, and the head coach's summary shows the change.

**The client has already paid:** the generator refuses. Nothing changes here. The coach adjusts that client's future invoices.
