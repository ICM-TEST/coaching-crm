# Setup questionnaire

Answers go into the Drive files named in brackets, never into this repo.

## The business
1. Trading name, website, payment wording and sign-off, as they should appear on invoices (a current invoice helps). (`factory/business`)
2. Bank name, account holder, account type and number, branch code (if any) and currency symbol, as printed on invoices. (`factory/business`)
3. VAT-registered? (`factory/business`. If yes, the invoice design changes.)
4. Day of the month invoices go out (invoices are due on receipt). (`factory/business`)

## People
5. Head coach: name, Google account, and do they coach? (`hub/<slug>.me`; `coach-<slug>/` if they coach)
6. Each coach: name, short code (2 letters, internal), Google account, **phone and email as printed on their invoices**,
   their own **coach number** (01–99, never shared or reused: it goes in every reference), and the **next invoice
   number** from their current app. (`hub/coaches`, `coach-<slug>/<slug>.me`)
7. Anyone who fetches bank statements but doesn't coach? (If yes, add the optional `bank-drop/` folder.)
Coaches are added one at a time after first-run setup (`workspace/roles/head-coach/skills/coaches.md`).

## Invoice look
- The Inter font files (`Inter-Regular/Medium/SemiBold/Bold.ttf`) in `factory/invoice-template/fonts/`.

## Billable work
8. Each item exactly as it's named on invoices (e.g. *Group session*): code, name, unit, price, and whether it's billed in advance or after. (`factory/billable-work`)

## Clients
9. Which details to keep about each client, beyond name, phone and email (only the head coach sees them).
10. Their current client list, in any form (spreadsheet, app export, PDF, document), to import.

The head coach's Claude asks all of this itself after first-run setup, and walks them through making the client form
(`workspace/roles/head-coach/skills/client-setup.md`). This list is only for preparing.
