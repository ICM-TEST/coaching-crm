# Error 500: reasons and requests

How `CLAUDE.md` rule 6 is answered. The Error 500 line is always exactly:

`Error 500 - Sorry, this request cannot be carried out`

It's followed by one reason line from the table below, then by the request offer (head coach) or the pointer (coach).

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

**Not Error 500.** These belong to the head coach, through their skills: the business details, prices and invoice wording
in `factory/`, coaches, clients, the head coach's own client details and the client form
([../roles/head-coach/skills/client-setup.md](../roles/head-coach/skills/client-setup.md)). A coach's own records, drafts
and corrections belong to the coach.

## After the reason line

- **Head coach:** ask "Want me to log a request to update the system?" On yes, ask in one message, numbered, in these
  words, leaving out any the chat has already answered:
  1. What should the system do?
  2. Give me one real example: who, when, what happened.
  3. How urgent is it, and what will you do until then?

  Ask once. Anything not answered goes in as `(not said)`; never ask again. Then write the Doc
  `hub/requests/YYYY-MM-DD-<slug>` through the Docs connector: `date:`, `from:` (the head coach's name), then each answer
  word for word under its own heading. Tell them in one line that it's logged for Ross. Writing it changes nothing else.
- **Coach:** don't offer a request: a coach's Claude writes nothing but invoices and invoice lists. Add one line: "If the
  system should do this, tell <head coach's first name>."

## Asked about Error 500

- What is it? Reply exactly: `Structure / system files cannot be changed or edited`
- Why? Reply exactly: `Structure is safe guarded from breaking or corrupting`
- Anything else about it: the Error 500 line again. Never how to get around it.
