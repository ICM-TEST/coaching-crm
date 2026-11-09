# setup/ — standing up a new business

Done once per business, by Ross with the head coach. Order matters: sharing is the step that's hard to undo.

## Process
Answers go only into the Drive files, never into this repo.

1. Create a **Google Workspace Shared Drive** named `<Business> CRM`. The head coach is its only member (*Manager*).
2. The head coach says "set up my workspace" ([SKILL.md](SKILL.md) asks for all of this). It builds the drive from the template, through the connectors (the head coach's Claude, [../shared/connectors.md](../shared/connectors.md)):
   copy `_templates/drive/` (without `coach-template/`) into an empty `work/`, fill `factory/business.txt` and
   `factory/billable-work.csv`, and run
   `scripts/sync.py plan` against an empty snapshot: it lists every folder, Sheet and Doc to create.
   If the head coach coaches, they're added too (`scripts/coaches.py add`): coach number 01, their own folder.
3. Then, one at a time and guided step by step by their Claude:
   - **each coach** ([../roles/head-coach/skills/coaches.md](../roles/head-coach/skills/coaches.md)): the next coach
     number, their folder, the head coach sharing it with them folder by folder, and a setup message for the coach;
   - **what's kept about each client, the client form and its link, and the current client list**
     ([../roles/head-coach/skills/client-setup.md](../roles/head-coach/skills/client-setup.md)).

## Human check
Every answer is read back before anything is written. Sharing is done by the head coach, folder by folder, following
the steps their Claude gives ([sharing-checklist.md](sharing-checklist.md) is the rule they follow). Nobody but the
head coach is a member of the shared drive.
