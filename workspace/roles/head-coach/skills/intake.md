# Skill — intake (form responses → main list)

## Inputs
- `hub/client-form responses`: the Form's response Sheet ([client-setup.md](client-setup.md), part 2)
- `hub/clients`, `hub/coaches`, `hub/start` (the scripts keep its counts right)
- The latest `hub/intake/…` Sheet (for its `last_row:` value, so rows aren't read twice)

## Process
1. Read Sheet rows after `last_row`. If there are none, say "no new responses" and stop.
2. For each row, find possible matches in `hub/clients` on phone, then email, then name. A match on
   phone or email = **same person** (returning or duplicate). A match on name only = **ask**.
3. Propose a coach: the coach the client named → their current coach if returning → blank.
4. Write a new `hub/intake/YYYY-MM-DD` Sheet with a `last_row:` / `<n>` row at the top, then a table:
   `row` · `name` · `phone` · `email` · each of the head coach's own details (`clients.py details`) · `named coach` ·
   `match` · `proposed coach` · `decision`.
   `decision` is pre-filled with `add`, `reactivate C0042` or `?`.

## Human check — STOP
The head coach reads the intake Sheet and fixes the `decision`s. Never merge or reactivate without them.

## After approval
- `add` → new row in `hub/clients` (next `C` number, `since` = today; status `active` with a coach, `new` without),
  with the answers to the head coach's own details in their columns.
- `reactivate Cxxxx` → set that row's status back to `active`, and its coach.
- Every change → one line in `hub/client-history`.
- Run `scripts/build_lists.py coach-clients`.
