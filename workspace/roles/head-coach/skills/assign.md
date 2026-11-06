# Skill — assign or move a client

## Inputs
- `hub/clients`, `hub/coaches`

## Process
1. Find the client. If more than one row fits the name, list them and ask.
2. Set `coach` (and status `active` if it was `new`). For **leaving**, set status `left` and keep `coach`
   as the last coach. Clients are never deleted.
3. Append to `hub/client-history`: `date` · `client_id` · `coach ben → hannah` · the reason given.
4. Run `scripts/build_lists.py coach-clients`.
5. @-mention the coaches affected.

## Rules
- **Open invoices stay with the coach who issued them.** Moving a client changes who invoices *from now on*.
- A one-off swap (coach B covers coach A's lesson) is **not** a move. The coach who taught it logs and bills it.
