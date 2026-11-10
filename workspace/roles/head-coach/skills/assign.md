# Skill — assign or move a client

## Inputs
- `hub/clients`, `hub/coaches`, `hub/start` (the scripts keep its counts right)

## Process
1. Find the client. If more than one row fits the name, list them and ask.
2. Set `coach` (and status `active` if it was `new` or `unallocated`). For **leaving**, set status `left` and keep `coach`
   as the last coach. Clients are never deleted.
3. Append to `hub/client-history`: `date` · `client_id` · `coach <old slug> → <new slug>` · the reason given.
4. Run `scripts/build_lists.py coach-clients`.

## Add one by hand
For a client who won't use the Form. Give them the next `C` id, append a row to `hub/clients` (id, name, phone, email, status
`active`, coach, since today), append to `hub/client-history`, then run `scripts/build_lists.py coach-clients`.

## Rules
- **Open invoices stay with the coach who issued them.** Moving a client changes who invoices *from now on*.
- A one-off swap (coach B covers coach A's lesson) is **not** a move. The coach who taught it logs and bills it.
