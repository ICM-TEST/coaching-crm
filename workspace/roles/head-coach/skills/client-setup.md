# Skill — client setup: what to keep, the client form, the current list

Three parts, done once after first-run setup and in this order. Each can be run again later on its own. The head coach
isn't a Claude or Google expert: give numbered steps, one action each, in plain words, one part at a time, and wait for
"done" before the next part. Answers come only from the head coach, in this chat.

Every job is read → run → write ([../../../shared/connectors.md](../../../shared/connectors.md)).

## 1. What to keep about each client: "what do we keep about clients?"

Every client always has a full name, phone and email (the name and phone are printed on invoices), plus their coach,
status, start date and notes.

1. Ask: "What else do you want to keep about each client? For example, who pays if it isn't the client." One detail
   per message, until they say that's all. Note for each whether a new client must answer it.
2. Read the list back. Say that only the head coach sees these: coaches' client lists show name, phone, email and
   status only. **STOP** for a yes.
3. `python3 scripts/clients.py --root <work> details --add "<detail>" "<detail>" …`, then write it through the sync plan.

## 2. The client form: "set up my client form"

New clients sign up through one Google Form that the head coach owns. Forms can't be built through the connectors,
so the head coach makes it, following your steps.

### The questions
The form asks, in this order:
- Full name · Mobile number · Email (all required)
- each detail from part 1, worded exactly as `clients.py details` shows it, required as agreed
- "Which coach are you with, or would you like?": a dropdown of every active coach's name, then "No preference"

Ask if they want anything else on it (agreeing to their terms, for example). Extra questions like that stay in the
responses Sheet only. Read the questions back. **STOP** for a yes.

### Make the form: give these steps, filled in
1. Go to forms.google.com, signed in as yourself, and press Blank form.
2. Click "Untitled form" and type a title, for example "<trading name>: new clients".
3. In the first question box, click "Untitled question" and type: Full name. In the menu on its right, choose Short
   answer. Switch on Required, at the bottom of the box.
4. Press the + on the right to add the next question. Do the same for Mobile number, then Email.
5. Add <each detail, one step per detail, typed exactly as given>: Short answer, Required <on or off>.
6. Add the last question: Which coach are you with, or would you like? Choose Dropdown in the menu, type each option:
   <every active coach's name, one per line>, then No preference. Switch on Required.
7. Say "done".

### Where the answers go
1. In the form, open the Responses tab at the top and press Link to Sheets.
2. Choose Create a new spreadsheet, name it exactly client-form responses, and press Create.
3. Go to drive.google.com. Find client-form responses (in My Drive), right-click it, choose Organise, then Move.
4. Open the business's folder, then hub, and press Move. If Drive asks about sharing, press Move again.
5. Never add a coach as an editor of the form: editors can see every answer.
6. Say "done".

### The link for new clients
1. Back in the form, press Send, at the top right.
2. Press the link symbol, tick Shorten URL, and press Copy.
3. Paste the link here.

Then write it into `factory/client-form` (`link: <the link>`) through the Docs connector, re-read it, and tell the head
coach: "This is the link for new clients. You and every coach can hand it out; coaches find it in factory/client-form.
When answers come in, say 'check intake'."

## 3. The clients you have now: "bring in my clients"

1. Ask: "Do you have a list of your current clients: a spreadsheet, an export from the app you use now, a PDF or a
   document? Attach it here, or put it in hub/ and tell me its name." No list: skip this part. Clients can join through
   the form, or be added one at a time ("add a client").
2. Read it. Work out which column, or part of each entry, holds each client's name, phone, email, coach, and each of
   the head coach's own details. Ask once about anything you can't place. Never make a value up: leave it blank.
3. In your sandbox (outside `work/`), write a CSV with the header `name,phone,email,coach,notes` followed by the head
   coach's details exactly as `clients.py details` shows them, one row per client, values copied exactly as the list
   has them. For a spreadsheet or CSV, convert it with a short script, never by retyping. For a PDF or document, write
   the rows from its text.
4. `python3 scripts/clients.py --root <work> import <file> --dry-run`. Tell the head coach how many clients it found, how
   many per coach, how many have no coach yet (they come in as unallocated), and every "Check:" line. If it refuses, fix
   the file from the list, or ask.
5. **STOP** for a yes.
6. `python3 scripts/clients.py --root <work> import <file>`, then write it through the sync plan. Each coach's client
   list updates by itself.
7. Offer to give each unallocated client a coach ([assign.md](assign.md)).
