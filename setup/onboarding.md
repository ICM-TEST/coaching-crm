# Onboarding a business: Ross only

The lock is a public repo that only Ross can write to. Claude's GitHub link only lets an organisation's owners use its
private repos, so a coach can't be given read-only access to a private one. A public repo needs no access at all.

## 1. Their Google side
The head coach says "set up my workspace" ([../workspace/setup/SKILL.md](../workspace/setup/SKILL.md)). Have [questionnaire.md](questionnaire.md) answered first.

## 2. Each person's Claude, at claude.ai on a computer
1. Turn on code execution, and connect Google Drive, Sheets and Docs under **their own** Google account.
2. Create a Project.
3. Project knowledge → **Add from GitHub** → this repo → **Configure files**: tick only `workspace`.
4. Paste their instruction into the **Instructions** panel: the head coach's from [project-instructions.md](project-instructions.md), a coach's from `scripts/coaches.py instructions <slug>`.
5. **Sync** once.

Don't add anyone as a collaborator or organisation member. Not being one is the lock.

## 3. Before every push
`tools/release.py` scans for personal data. Its deny list is kept outside the repo, because the list itself names real people.
