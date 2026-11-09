# Skill — coaches: add one, remove one

The head coach isn't a Claude or Google Drive expert, and neither are the coaches. Every step you give is numbered,
one action each, in plain words. Give one part at a time and wait for "done" before the next.

Every job is read → run → write ([../../../shared/connectors.md](../../../shared/connectors.md)). Read `hub/coaches`,
`hub/clients`, the head coach's `<slug>.me`, `factory/business` and `factory/invoicing-runs`.

## Add a coach: "add a coach", "set up <name>"

### Ask, one question per message
Answers come only from the head coach, in this chat.
1. Their full name, as printed on their invoices.
2. Their phone number and email, as printed on their invoices.
3. The Google account they'll use for Google Drive and Claude. Often the same email: ask.
4. Their next invoice number, from the app they invoice with now (skip: they start at 1).

### Human check: STOP
Read it back in one message. Wait for a yes.

### Make their folder
1. `python3 scripts/coaches.py --root <work> add --name "…" --phone "…" --email … --google … --invoice-start …`
   It gives them the next coach number, and makes their folder and their `<slug>.me` Doc.
2. If an invoicing run is open, `python3 scripts/runs.py --root <work> open <period>` again, so they get its month folder.
3. Write it: `python3 scripts/sync.py plan <work> --role head-coach`, then carry out the plan. Re-read their `.me` Doc.

### Sharing: the head coach does it, you guide
`python3 scripts/coaches.py --root <work> share <slug>` prints the steps. Give them exactly as printed, and wait for
"done". You never share anything yourself, and the coach is never made a member of the whole shared drive.

### Their setup message
`python3 scripts/coaches.py --root <work> welcome <slug>` prints the coach's step-by-step setup, with their Project
instruction inside it. Give it to the head coach in one message, to send to the coach as it is (WhatsApp or email).
It holds no client details.

### Check it worked
The coach sends the head coach their Claude's answer to "Who do you work for?". When the head coach shows you, check
it names that coach, their coach number and folder, and says it can't open `hub/`.
- A different name or number: the instruction was pasted wrong. Give the welcome message again.
- It can open `hub/` or another coach's folder: the sharing is wrong. Go through the share steps again together.
- It can't open its own folder: the folder isn't shared yet, or the coach connected a different Google account.

## Remove a coach: "<name> is leaving", "remove <name>"

### Human check: STOP
Read back: their name and coach number, how many of their clients will become **unallocated**, and that their
invoices stay theirs: payments for them are still matched at the bank recon. Wait for a yes.

### Run
1. `python3 scripts/coaches.py --root <work> leave <slug>`. They're marked as left (their number is never reused), and
   every active or new client of theirs becomes `unallocated`, with a line in `hub/client-history`.
2. Write it through the sync plan, as above.

### Remove their access: the head coach does it, you guide
`python3 scripts/coaches.py --root <work> unshare <slug>` prints the steps. Give them exactly as printed, and wait for
"done".

### Then
List the unallocated clients and offer to give each one a new coach ([assign.md](assign.md)).
