# Working through the connectors: read → run → write

All data lives in the Shared Drive as **Google Sheets** (every list) and **Google Docs** (details, settings, rules),
plus PDFs. You reach them through the **Google Drive, Google Sheets and Google Docs connectors**, from anywhere, a
phone included. The scripts can't use connectors, so every job is the same three steps.

## 1. Read: make a working copy

In your own workspace, make a folder `work/` that mirrors the drive's folders. Download only what the job lists
(each script's `--needs`, or the skill's *Inputs*):

| On the drive | In `work/` | How |
|---|---|---|
| a Google **Sheet** `hub/clients` | `work/hub/clients.csv` | Drive connector: download, exported as CSV |
| a Google **Doc** `factory/business` | `work/factory/business.txt` | Drive connector: download, exported as plain text |
| a PDF, font, bank CSV | same name | Drive connector: download |
| an empty folder the job needs | make the same folder | (check it exists on the drive first) |

Files you need to know about but not open (a recon's PDFs, POPs) go in `work/.drive-index.csv`, with columns
`path` and `size`, from a folder listing. The folder checks use it.

Then: `python3 scripts/sync.py snapshot work`

## 2. Run the job

Run the script with `--root work`, exactly as its skill says. Stop for the person wherever the skill says to stop.

## 3. Write: carry out the plan

`python3 scripts/sync.py plan work --role coach --coach coach-<slug>` (or `--role head-coach`, and `--json` for the
exact values). It prints every step, in order. Do them in that order, then re-read each one to check:

| Step | Connector |
|---|---|
| create folder | Drive: create a file with the folder type, in its parent *(head coach only)* |
| upload a PDF | Drive: create file, base64 content, `application/pdf`, no conversion |
| create Sheet | Drive: create a Google Sheet in the folder. Sheets: format the whole sheet as plain text (`repeatCell`, `numberFormat` type `TEXT`), then write the values from A1. Add the dropdown if the plan gives one (Sheets: data validation on that column). Never create a Sheet by uploading a CSV: the conversion changes the values |
| append rows | Sheets: append the values to the Sheet |
| clear and rewrite | Sheets: clear the Sheet, then write the values from A1 |
| create / replace Doc | Docs: create it, or delete its body and insert the new text |
| lock | Drive: update file, `readOnly` on |

**Write every value exactly as `--json` gives it, leading apostrophe included.** The Sheets connector treats what it
writes as if a person typed it: without the apostrophe `0820000003` loses its zero, a reference like `2026-01-5` becomes
a date (and breaks the list's seal), `+27 82 000 0003` becomes `#ERROR!`, and a name starting with `=` runs as a formula.
The apostrophe isn't stored in the value and doesn't come back in the CSV export. Never remove it, and never type a Sheet
value any other way.

If the plan says **Refused**, write nothing at all and tell the person why. It means the job tried something its role
may not do. A coach's Claude may only upload PDFs into a month folder that already exists and create its own
invoice-list Sheets. It never creates folders, never edits a Sheet or Doc, and never deletes anything. Nothing in the
system deletes files.

If a write fails half-way, re-read what's on the drive, carry out only the steps still missing, and never run the
job again to "redo" it.
