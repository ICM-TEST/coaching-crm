# schemas — every data file, its columns, and its one writer

Every **list is a Google Sheet** and every **other data file a Google Doc**; PDFs, POPs, bank statements and fonts stay files.
They're reached through the Google connectors, as read → run → write ([connectors.md](connectors.md)). In the working
copy a Sheet is `<name>.csv` and a Doc `<name>.txt`; on the drive they have no extension.

- **A Sheet** may open with a few title/note rows (starting `#`) and `key:` / value rows, then a blank row, then its table
  (header row, then one row per record). A generated Sheet can hold several tables, each after a `## Heading` row.
- **A Doc** holds `key: value` lines (one per line), plus any free text.
- Dates are `YYYY-MM-DD`; amounts plain numbers (`1400.00`), no currency sign. Values are written as plain text, as [connectors.md](connectors.md) says.

## The Drive tree

```
<Business> CRM            Google Workspace Shared Drive
├─ hub/                   head coach only
├─ factory/               all coaches: Viewer
├─ coach-<slug>/          that coach only: Contributor (one per coach, the head coach included)
└─ _archive/              head coach only
```

## hub/ — head coach only

| File | Columns | Writer |
|---|---|---|
| `<slug>.me` (Doc) | the head coach's details: `name`, `slug`, `role: head-coach`. Every `.me` Doc is named after its person | setup |
| `coaches` | **the head coach's list of coaches:** `number` (coach number, never reused) · `slug` · `code` · `name` · `phone` · `email` · `invoice_start` · `active` · `google_account` (what their folders are shared with) | `scripts/coaches.py` (add, leave); head coach for edits |
| `clients` | **the head coach's list of clients:** `id` · `name` (full name, as printed on invoices) · `phone` (printed on invoices) · `email` · `status` (`new` · `active` · `unallocated`: their coach left · `left`) · `coach` (the last coach, while unallocated) · `since` · `notes` · then the head coach's own details, seen only here (`scripts/clients.py details`) | head coach; `clients.py import` |
| `client-form responses` | the client form's answers, one column per question | Google Forms |
| `client-history` | `date` · `client_id` · `change` · `reason` | head coach (append) |
| `intake/YYYY-MM-DD` | intake proposal | head coach's Claude |
| `bank/` | the bank's statements, exactly as the bank gives them: CSV or PDF, never changed | head coach (uploads) |
| `bank/lines/<statement file name>` | **the lines read from that statement**, one layout for every bank: `date` (YYYY-MM-DD) · `description` (as printed) · `amount` (a plain number: money in positive, money out negative) · `balance` (after the line, as printed, or blank if the statement has none). One row per transaction, in the statement's order | the head coach's Claude, once per statement |
| `eft-ledger` | `eft_id` · `date` · `amount` · `description` · `source` | `recon.py` (append) |
| `eft-reviews` | `eft_id` · `date` · `verdict` (`client` / `non-client`) · `recon` | `recon.py` (append): the head coach's verdict on money the recon couldn't place |
| `all-invoices` | the head coach's **own copy** of every sealed invoice row: `coach` · `list` · `seal` · `archived` · then the invoice-list columns. **The books work from this copy**, so a coach's list changed or deleted later loses nothing | recon steps (append) |
| `allocations` | `id` · `date` · `recon` · `eft_id` · `coach` · `client_id` · `invoice` · `amount` · `kind` · `note` | `recon.py` (append), **the single source of every payment fact** |
| `pops/` | proofs of payment that reached the head coach directly (most come through coaches' `pops/` folders) | head coach |
| `pop-register` | `file` (path from the drive root) · `read_on` · `date` · `amount` · `payer` · `reference` · `client` · `invoice` | head coach's Claude, reading each POP |
| `recon/bank-YYYY-MM-DD`, `recon/pop-YYYY-MM-DD` | the two recons' proposals: `decision` column edited by the head coach | `recon.py bank` / `pops`, then the head coach |
| `unreconciled` | generated: the **live list** (client money not yet tied to an invoice), money not yet reviewed, POPs waiting | `recon.py` |
| `summary` | generated: totals by coach · **every unpaid invoice across all coaches, with days unpaid** · overpayments to handle in the head coach's own accounting | `recon.py` |

## factory/ — coaches can read, only the head coach writes

| File | Columns | Writer |
|---|---|---|
| `business` (Doc) | everything on the invoice that's the same for every coach: trading name, website, bank details, the payment and sign-off wording, `invoice_number_format`, `currency_symbol`, `invoice_day`, `payment_terms` | head coach |
| `client-form` (Doc) | `link:` the client form's link for new clients, which the head coach and every coach hand out | the head coach's Claude ([../roles/head-coach/skills/client-setup.md](../roles/head-coach/skills/client-setup.md)) |
| `invoice-template/fonts/` | Inter font files for the invoices | head coach |
| `billable-work` | `code` · `name` (as printed) · `unit` · `rate` · `billed` (`in advance`: can bill next month's sessions · `after`: the month past) | head coach |
| `invoicing-runs` | `period` · `opened` · `due` · `status` | `runs.py open` |
| `invoice-rules`, `invoice-template/` | *designed in the invoice-design stage* | head coach |

## coach-&lt;slug&gt;/ — one coach

**A coach produces exactly two things per invoicing run: the run's invoice list and its PDFs.**
Everything else in the folder comes from the head coach.

| File | Holds | Writer |
|---|---|---|
| `<slug>.me` (Doc) | **generated from the coach's row in `hub/coaches`:** `name`, `slug`, `code`, `coach_number`, `phone`, `email` (printed on their invoices), `invoice_start`, `role: coach` | `build_lists.py` / every recon step |
| `invoice-lists/<month>` | **Output 1.** One run's invoices (format below) | invoice generator (coach), once, at issue |
| `invoices/<period>/*.pdf` | **Output 2.** The PDFs the coach sends to clients. The `<period>/` folder is made by `runs.py open` (head coach) | invoice generator (coach), at issue |
| `clients` | this coach's clients: `id` · `name` · `phone` · `email` · `status` · `since`. Updates by itself when the head coach assigns or moves a client. | `build_lists.py` after every main-list change, and again at every recon step |
| `unpaid` | **the only money information a coach gets:** their unpaid invoices, longest unpaid first (amount, still owed, days unpaid). An invoice not listed is settled. | `recon.py` |
| `pops/` | proofs of payment from this coach's clients, uploaded by the coach (invoice number in the file name if known). Not a Claude output: the coach uploads them. The POP recon only uses them for **this coach's** invoices. | the coach, by hand |

### The invoice list (a Sheet)

```
---
coach: <slug>
period: 2026-11
issued: 2026-12-01
---

# Invoice list — <name> — 2026-11

| number | date | client_id | client | payer | reference | amount | applies_to | pdf | pdf_sha |
```

- `payer`: who pays, if not the client (a parent, for example). Recon matches bank lines on this name too.
- `number`: the internal id, with the coach's code (`<coach code>-2026-0490`). Unique across all coaches.
- `reference`: the printed invoice number, which is also the payment reference: `2026-03-490` (year-coach number-invoice
  number). Unique across coaches. Recon still never pays on a reference that fits two clients.
- **An updated invoice** is a row in a later list (`2026-10-2`) with the same `number` and `reference`, the new `amount`, and
  `applies_to` = its own `number`. The latest sealed version is the invoice. Every version stays on its list and in `all-invoices`.
- Frontmatter also carries `made_by: issue.py` and a **`seal`** over the list's contents, and each row a `pdf_sha`
  (the PDF's fingerprint). Recon trusts only sealed, unchanged lists; anything else is left out and reported.
- A Sheet with no `period:` row at the top isn't a list.
- A list is never edited after issue. An unpaid invoice is changed by re-issuing it through the generator. A paid one stays as
  it is, and the coach adjusts the client's future invoices. There are no credit notes.
- **A run is done** when a list for that period exists. With nothing to bill, the list has no rows.

### Derived figures

- **Every incoming EFT** is in exactly one state: *matched* (fully allocated) · *non-client* (verdict) ·
  *unreconciled* (verdict `client`, money left over: the live list) · *unreviewed* (no verdict yet, asked again at every recon).

- **Invoice balance** = the latest `amount` − allocations to it (`payment`, `write-off`).
- **Days unpaid** = today − invoice date (invoices are due on receipt).
- **Overpayments** (`overpayment` allocations) are listed on `hub/summary` only. This system keeps no client credit.
