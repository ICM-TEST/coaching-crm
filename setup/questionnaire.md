# Setup questionnaire

Answers go into the Drive files named in brackets, never into this repo.

## The business
1. A copy of a current invoice: trading name, website, payment wording and sign-off are copied from it exactly. (`factory/business`)
2. Bank, account holder, account type and number, branch code, as printed on invoices. (`factory/business`)
3. VAT-registered? (`factory/business`. If yes, the invoice design changes.)
4. Bank used, and a CSV export with names and amounts blanked out? (`hub/settings`: column names, date format)
5. Day of the month invoices go out, and payment terms? (`factory/business`)

## People
6. Head coach: name, Google account, and do they coach? (`hub/me`; `coach-<slug>/` if they coach)
7. Each coach: name, short code (2 letters, internal), Google account, **phone and email as printed on their invoices**,
   their own **coach number** (01–99, never shared or reused: it goes in every reference), and the **next invoice
   number** from their current app. (`hub/coaches`, `coach-<slug>/me`)
8. Anyone who fetches bank statements but doesn't coach? (If yes, add the optional `bank-drop/` folder.)

## Invoice look
- The Inter font files (`Inter-Regular/Medium/SemiBold/Bold.ttf`) in `factory/invoice-template/fonts/`.

## Billable work
9. Each item exactly as it's named on invoices (e.g. *Group Squad*): code, name, unit, price. (`factory/billable-work`)

## The Google Form
Required questions, alongside the business's own:
- Full name · Mobile number · Email
- New or existing client?
- Which coach are you with / were you referred by? (dropdown of coach names, plus "No preference")
