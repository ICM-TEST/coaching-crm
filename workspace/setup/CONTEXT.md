# setup/ — standing up a new business

Done once per business, by Ross with the head coach. Order matters: sharing is the step that's hard to undo.

## Process
1. Ross collects the answers with the head coach. They go only into the Drive files, never into this repo.
2. Create a **Google Workspace Shared Drive** named `<Business> CRM`. The head coach is *Manager*.
3. The head coach says "set up my workspace" ([SKILL.md](SKILL.md) asks for all of this). It builds the drive from the template, through the connectors (the head coach's Claude, [../shared/connectors.md](../shared/connectors.md)):
   copy `_templates/drive/` (without `coach-template/`) into an empty `work/`, fill `factory/business.txt` and
   `factory/billable-work.csv`, and run
   `scripts/sync.py plan` against an empty snapshot: it lists every folder, Sheet and Doc to create.
   Then add every coach, the head coach first, with `scripts/coaches.py add` (name, phone, email, next invoice number)
   and write its plan the same way. Each coach gets the next **coach number** (01, 02, …), their own folder, their
   `me` Doc, and empty `clients` and `unpaid` Sheets.
4. Create the Google Form (the head coach's account) with the questions Ross gives you. Link it to a response Sheet in `hub/`.
5. **Ross reads the folder tree and [sharing-checklist.md](sharing-checklist.md) before any sharing is applied.**
6. Apply the sharing exactly as the checklist says. Tick each line.
7. Ross sets up one Claude Project per person: the whole repo attached from GitHub (every folder ticked), code execution on, and the Google
   connectors under their own account. `scripts/coaches.py instructions <slug>` or `instructions head-coach` prints each
   person's Project instruction. Every job is then read → run → write ([../shared/connectors.md](../shared/connectors.md)).

## Human check
Step 5. Nothing is shared until Ross has read the tree and the checklist.
