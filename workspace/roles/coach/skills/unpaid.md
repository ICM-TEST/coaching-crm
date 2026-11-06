# Skill — unpaid

You read; you don't write. This coach's Claude makes invoices and invoice lists, and nothing else.

## Inputs
- `unpaid` only. It is rebuilt by the head coach's recon; its header says when.

## "Who hasn't paid?"
List the unpaid invoices, longest unpaid first: number · client · still owed · days unpaid. Say when the list was last
updated. Any ⚠ note at the top of the file: pass it on as written.

**"Has <client> paid <invoice>?"** If it's on `unpaid`, no (or only partly: say what's still owed). If it's in
an invoice list but not on `unpaid`, it's settled. That's all there is to know. No dates or amounts received.

## "They say they've paid"
The coach asks the client for proof of payment and uploads it to their `pops/` folder, with the invoice number in the
file name if they know it (for example `2026-03-490 Peter.pdf`). The head coach's POP recon picks it up.

## Write-offs, overpayments, credits, refunds
Not something you record or write. The coach agrees write-offs with the head coach directly; overpayments, credits and
refunds are the head coach's to handle.
