# Working through the connectors: read → run → write

All data lives in the Shared Drive as **Google Sheets** (every list) and **Google Docs** (details, settings, rules),
plus PDFs. You reach them through the **Google Drive, Google Sheets and Google Docs connectors**, from anywhere, a
phone included. The scripts can't use connectors, so every job is the same three steps.

## 0. Get the scripts

The rules attached to your Project can be read but not run, and the scripts aren't attached at all. So before the
first script in a chat, copy the public repo into the sandbox with git, **at the version your rules are**: `<version>`
is the `version:` in [../version.md](../version.md), so the code you run always matches the rules you hold.

```
git clone --depth 1 --branch v<version> https://github.com/ICM-TEST/coaching-crm.git coaching-crm-main
```

Only if the sandbox has no `git` command, use the download link instead. It redirects to `codeload.github.com`, which
some sandboxes block:

```
curl -sSL https://github.com/ICM-TEST/coaching-crm/archive/refs/tags/v<version>.tar.gz | tar xz
```

(that unpacks as `coaching-crm-<version>`: rename it `coaching-crm-main`). Never download `main` or any other branch or
version: a newer one may not match your rules.

Run every `python3 scripts/…` from `coaching-crm-main`, with `--root` and `work` as the full path of your `work/`.
If the folder is already there, use it. **These are the only two ways. If they fail, stop and tell the person the exact
error.** Don't retype the scripts by hand, fetch them from anywhere else, or look for another way.

## 1. Read: make a working copy

In your sandbox's own working folder (never one whose files are shown in the chat), make a folder `work/` that
mirrors the drive's folders. Download only what the job lists
(each script's `--needs`, or the skill's *Inputs*):

| On the drive | In `work/` | How |
|---|---|---|
| a Google **Sheet** `hub/clients` | `work/hub/clients.csv` | Drive connector: download, exported as CSV |
| a Google **Doc** `factory/business` | `work/factory/business.txt` | Drive connector: download, exported as plain text |
| a PDF or other file | same name | Drive connector: download |
| the invoice fonts (coach, when issuing) | `work/factory/invoice-template/fonts/` | Copy from `_templates/drive/factory/invoice-template/fonts/` in the downloaded repo, before the snapshot. They aren't on the drive |
| an empty folder the job needs | make the same folder | (check it exists on the drive first) |

**Download nothing the job doesn't list.** One download is one Drive call: never fetch a file to "have a look", and
never fetch the same file twice in a chat.

Files you need to know about but not open (a recon's PDFs, POPs, invoice lists already copied) go in
`work/.drive-index.csv`, with columns `path`, `size` and `modified` (the file's last-modified date, YYYY-MM-DD), from a
folder listing. The folder checks use it, and `recon.py lists-needed` uses it to say which invoice lists to download.

Then: `python3 scripts/sync.py snapshot work`

## 2. Run the job

Run the script with `--root work`, exactly as its skill says. Stop for the person wherever the skill says to stop.

## 3. Write: carry out the plan

`python3 scripts/sync.py plan work --role coach --coach coach-<slug>` (or `--role head-coach`, and `--json` for the
exact values). It prints every step, in order. Do them in that order, quietly (the person never sees the plan or the
steps). **Don't re-read each file afterwards.** A connector call that returns without an error has landed. When the plan
is done, check once: list each folder you wrote into, and re-read one Sheet that holds phone numbers or references to
see the values came back exact. Re-read another file only if a call failed or that check is wrong.

| Step | Connector |
|---|---|
| create folder | Drive: create a file with the folder type, in its parent *(head coach only)* |
| hand over (coach's PDFs) | no connector: give the coach the file in the chat. A coach's PDFs are never uploaded |
| upload a file *(head coach only)* | Drive: create file, base64 content, no conversion |
| create Sheet | Drive: create a Google Sheet in the folder. Sheets: format the whole sheet as plain text (`repeatCell`, `numberFormat` type `TEXT`), then write the values from A1. Add the dropdown if the plan gives one (Sheets: data validation on that column). Never create a Sheet by uploading a CSV: the conversion changes the values |
| append rows | Sheets: append the values to the Sheet |
| clear and rewrite | Sheets: clear the Sheet, then write the values from A1 |
| create / replace Doc | Docs: create it, or delete its body and insert the new text |
| lock | Drive: update file, `readOnly` on |

**Write every value exactly as `--json` gives it, leading apostrophe included.** The Sheets connector treats what it
writes as if a person typed it: without the apostrophe a phone number loses its leading zero, a reference like `2026-01-5` becomes
a date (and breaks the list's seal), one starting with `+` becomes `#ERROR!`, and a name starting with `=` runs as a formula.
The apostrophe isn't stored in the value and doesn't come back in the CSV export. Never remove it, and never type a Sheet
value any other way.

If the plan says **Refused**, write nothing at all and tell the person why. It means the job tried something its role
may not do. A coach's Claude writes one kind of thing to the drive: its own invoice-list Sheets. It never uploads a
file, never creates folders, never edits a Sheet or Doc, and never deletes anything. Nothing in the
system deletes files.

If a write fails half-way, re-read what's on the drive, carry out only the steps still missing, and never run the
job again to "redo" it.
