Invoice lists

One file per invoicing run, named <month> (for example 2026-11), a Google Sheet. Only the invoice generator
(scripts/issue.py, run from the coach's own Claude Project) makes these. It seals each list and records each PDF's
fingerprint. Nothing edits a list afterwards; an updated invoice gets a new sealed list.

The head coach's recon checks every list's seal at each recon. The PDFs go to the coach in the chat and aren't kept on the drive. A list typed or changed by hand, for example
by a Claude chat outside the coach's Project, is left out of the books and reported to the coach and the head coach.
A run counts as done only when its sealed list exists. With nothing to bill, the generator issues an empty list.
