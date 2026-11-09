# Skill: first-run setup, "set up my workspace"

Head coach only, once per business. Their Drive has no `hub/` yet. If it has one, say it's already set up and stop.

## Ask, one question per message

Keep each message short. "Skip" is fine where marked.

**Every answer comes from the person, in this chat.** Never fill one in or suggest one from memory, earlier chats,
other Projects or anything you know about this business. Never name a bank, country, currency or format they haven't
given: ask about "your bank" and "your invoices". The `<placeholders>` in the templates say what to ask for, nothing more.

1. **Which folder?** The name of the Shared Drive (or the shared folder standing in for it). Find it with the Drive
   connector and read back its name. If it isn't empty, say what's in it and ask before going on.
2. **The business, as printed on the invoices:** trading name, website (skip), account holder, bank name, branch code
   (skip), account type (skip), account number, and the currency symbol printed before amounts.
3. **Invoice wording:** show the default `payment_instruction`, `pop_request`, `thanks` from `factory/business`, and ask them
   to keep it or paste their own. Then the sign-off.
4. **Invoice day:** the day of the month invoices go out (1 to 28). Invoices are due on receipt.
5. **The price list:** each item as named on invoices, its price, its unit, and whether it's billed in advance (paid up
   front, so an invoice can include next month's sessions) or after (for the month past). Make a short code for each.
6. **You:** full name, phone and email as printed on invoices, next invoice number. Do you coach? (Assume yes.)

There's no question about bank statements: the bank recon reads whatever the bank gives, CSV or PDF, when it runs.

## Human check: STOP

Read everything back in one message. Wait for a yes. Nothing is written to the drive before it.

## Build

Follow [../shared/connectors.md](../shared/connectors.md).

1. Get the scripts (step 0 there). Make an empty `work/`, then `python3 scripts/sync.py snapshot <work>`.
2. Copy `_templates/drive/` into `work/`, leaving out `coach-template/` and `factory/invoice-template/fonts/`: the fonts
   come with the scripts, and uploading them through a connector is wasteful.
3. Fill in `factory/business.txt` and `factory/billable-work.csv`, replacing every `<placeholder>` (a skipped one becomes
   blank), and write `hub/<slug>.me.txt`, which becomes the Doc `<slug>.me`
   (`name`, `slug`, `role: head-coach`).
4. If the head coach coaches: `python3 scripts/coaches.py --root <work> add --name … --phone … --email … --invoice-start …`.
   They get coach number 01 and their own folder. Other coaches come after setup, one at a time (*Finish*).
5. `python3 scripts/sync.py plan <work> --role head-coach --json`. Say how many steps it lists, then carry them out in
   order inside the folder from question 1, with a one-line progress note every so often. If a write fails, re-read what's on
   the drive and do only the steps still missing.
6. List the folders on the drive and re-read one Sheet to check the phones came back exact.

## Finish

Tell them, in this order:
- What was created, and anything that failed.
- Their next steps, numbered, and offer to start the first one now. Each one, I guide you through step by step:
  1. **Add your coaches**, one at a time: say "add a coach". For each, I give you the steps to share their folders with
     them, and a step-by-step setup message to send them ([../roles/head-coach/skills/coaches.md](../roles/head-coach/skills/coaches.md)).
  2. **Choose what you keep about each client**: say "what do we keep about clients?".
  3. **Make your client form** for new clients, and get the link to give them: say "set up my client form".
  4. **Bring in your current clients** from a list you already have: say "bring in my clients".
  (2 to 4: [../roles/head-coach/skills/client-setup.md](../roles/head-coach/skills/client-setup.md).)
- Bank statements: upload each one to `hub/bank/` as the bank gives it, CSV or PDF, then say "run recon".
