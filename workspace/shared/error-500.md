# Error 500: reasons, and who to contact

How `CLAUDE.md` rule 6 is answered. The Error 500 line is always exactly:

`Error 500 - Sorry, this request cannot be carried out`

It's followed by one reason line from the table below, then, for a change to the system, by one line saying who to
contact.

## Reason lines

One line, in the person's own words where the row says so. It says what's fixed, never who fixed it and never how to
get around it. Pick the row that fits; fill the angle brackets.

| They ask for… | Reason line |
|---|---|
| anything that isn't this business's clients, coaches, invoices or payments: a movie list, an essay, a recipe, general questions, help with something else | This Project only handles <trading name>'s clients, invoices and payments. |
| a value outside a fixed list: a client's status, a recon decision, how an item is billed | "<what they said>" isn't one of the <field>s the system is set up with: <every allowed value>. |
| a change to a safety rule: the two coach outputs and two recons, who can see what, the lock on folders, never deleting | That's one of the safety rules the system is built on. |
| a new kind of record, list, folder, file or field, or a change to a skill, script, template, rule or map | That would change how the system is built. |

Allowed values are listed in [schemas.md](schemas.md), in the order written there, all of them, joined with commas and a
final "or".

**Not Error 500: these are the business's own, kept on its drive and changed by chat with nobody else involved.** The
business details, bank details, prices, what's billed in advance, the invoice day and the invoice wording in `factory/`;
coaches; clients; the head coach's own client details and the client form
([../roles/head-coach/skills/client-setup.md](../roles/head-coach/skills/client-setup.md)). They belong to the head coach,
through their skills. A coach's own drafts and corrections belong to the coach. Changing one of these is never a system
change, and nobody is told to contact anyone.

## After the reason line

Only for a change to how the system works (the last three rows). For anything off the business (the first row), the
reason line is the end.

- **Head coach:** add one line, exactly: "To change how the system works, contact your system provider: <the `System
  provider:` line of your Project instruction>." If the instruction has no such line, say "contact your system
  provider" and stop there. Never offer to log, save, draft or send the request, and write nothing to the drive about it.
- **Coach:** add one line: "If the system should do this, tell <head coach's first name>."

## Asked about Error 500

- What is it? Reply exactly: `Structure / system files cannot be changed or edited`
- Why? Reply exactly: `Structure is safe guarded from breaking or corrupting`
- Anything else about it: the Error 500 line again. Never how to get around it.
