# Sharing checklist

Confidentiality rests entirely on these lines. Tick each one at setup, and again whenever a coach joins or leaves.

## Shared Drive membership
- [ ] The **only** Shared Drive member is the head coach (*Manager*). Coaches are **not** members of the drive itself.
      *(Members of the drive can see every folder in it. Coaches get access folder by folder.)*
- [ ] Ross: *Content manager* only if the head coach agrees. Otherwise Ross gets no access to data.

## Folders
- [ ] `hub/`: no one added beyond the drive's members.
- [ ] `factory/`: every active coach added as **Viewer**.
- [ ] each `coach-<slug>/`: **that coach only**, as **Viewer**, so `me`, `clients` and `unpaid` can't be changed
      by the coach or any Claude chat of theirs.
- [ ] inside it, `invoice-lists/`, `invoices/` and `pops/`: **that coach**, as **Contributor** (can add and edit, and can share individual files; can't
      delete or move files, or share folders). Those are the only places a coach writes. *(Pilot check: Drive allows raising access on a
      subfolder; confirm it on the real drive.)*
- [ ] `_archive/`: no one added.

## Google Form
- [ ] Coaches are **not** Form collaborators or editors (editors can see every response).
- [ ] The response Sheet sits in `hub/` and isn't shared.
- [ ] Coaches have the fill-in link (`…/viewform`) only.

## Accounts
- [ ] Two-step verification is on for the head coach's Google account, every coach's Google account, and the GitHub organisation.

## GitHub
- [ ] Nobody but Ross is a collaborator or member. The repo is public, so coaches read it without access. Not being a member is the lock on the rules.

## When a coach joins
- [ ] `scripts/coaches.py add --name … --phone … --email … --invoice-start …` (gives the next coach number).
- [ ] Share `coach-<slug>/` with them as **Viewer**; its `invoice-lists/`, `invoices/` and `pops/` as **Contributor**;
      and `factory/` as **Viewer**.
- [ ] Set up their Claude Project: this repo's `workspace` folder only (Project knowledge → Add from GitHub → Configure files), code execution on, the Google Drive, Sheets and Docs connectors under
      **their** account, and the named instruction that
      `coaches.py add` printed. Then ask it **"Who do you work for?"** It must answer with their name, coach number and
      folder, and say it can't open `hub/` or another coach's folder. If it names anyone else, or says *stop*, fix the
      instruction or the sharing before they use it.

## When a coach leaves
- [ ] `scripts/coaches.py leave <slug>` (sets `active: no`; their number is never reused). Their folder and invoices stay;
      recon keeps matching payments to them.
- [ ] Remove them from `coach-<slug>/` and `factory/`.
- [ ] Reassign their clients (head coach → *assign*).

> **To build:** `scripts/check_sharing.py`, which lists every folder's sharing through the Drive API and flags any line above
> that doesn't hold. Until then, this checklist is done by hand.
