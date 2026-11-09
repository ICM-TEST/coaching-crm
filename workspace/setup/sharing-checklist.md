# Sharing checklist

Confidentiality rests entirely on these lines. The head coach follows them through the steps their Claude gives
(`scripts/coaches.py share` and `unshare`, from [../roles/head-coach/coach-steps.md](../roles/head-coach/coach-steps.md)).

## Shared Drive membership
- [ ] The **only** Shared Drive member is the head coach (*Manager*). Coaches are **not** members of the drive itself.
      *(Members of the drive can see every folder in it. Coaches get access folder by folder.)*
- [ ] Ross: *Content manager* only if the head coach agrees. Otherwise Ross gets no access to data.

## Folders
- [ ] `hub/`: no one added beyond the drive's members.
- [ ] `factory/`: every active coach added as **Viewer**.
- [ ] each `coach-<slug>/`: **that coach only**, as **Viewer**, so their `.me` Doc, `clients` and `unpaid` can't be changed
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

## When a coach joins or leaves
The head coach's Claude walks through it: [../roles/head-coach/skills/coaches.md](../roles/head-coach/skills/coaches.md).
Joining ends with the coach's Claude answering **"Who do you work for?"** with their name, coach number and folder, and
saying it can't open `hub/`. Leaving makes their active clients `unallocated`, and removes their access from all five
folders: access given directly on a subfolder stays until it's removed there too.

> **To build:** `scripts/check_sharing.py`, which lists every folder's sharing through the Drive API and flags any line above
> that doesn't hold. Until then, this checklist is done by hand.
