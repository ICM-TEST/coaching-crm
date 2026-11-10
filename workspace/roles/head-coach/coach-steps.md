# Coach steps: the texts `scripts/coaches.py share | welcome | unshare <slug>` print

The people reading these aren't Claude or Google Drive experts. Keep every step numbered, one action each, with the exact
button names. `coaches.py` fills in each `{placeholder}` from the head coach's list of coaches. Never put client details here.

## share

Share {first}'s folders with {first}. It takes about 5 minutes, on a computer.

{first}'s Google account: {google}

1. Go to drive.google.com, signed in as yourself.
2. Open the business's folder: the one with hub, factory and the coach folders in it.
3. Right-click the folder factory, then choose Share, then Share again.
4. Type {google}, set the access next to it to Viewer, and press Send.
5. Right-click the folder {folder}, then Share, then Share. Type {google}, set Viewer, and press Send.
6. Double-click {folder} to open it. Inside are three folders: invoice-lists, invoices and pops.
7. Share each of those three the same way, but set the access to Contributor. In a folder in My Drive rather than a
   shared drive, the same choice is called Editor.
8. Share nothing else. Never add {first} as a member of the whole shared drive: members can see every folder,
   including hub with everyone's payments.
9. Come back here and say "done".

## welcome

Hi {first}, here's how to set up your invoicing assistant for {business}. You do this once, on a computer, and it takes
about 15 minutes. After that it works from your phone too. If anything on your screen looks different from these steps,
stop and send {head} a screenshot.

You need a Claude account (claude.ai) and your Google account, {google}.

1. Check your folders. Go to drive.google.com, signed in as {google}, and click "Shared with me". You should see two
   folders: {folder} and factory. If you don't, tell {head} and stop here.
2. Go to claude.ai and sign in.
3. Turn on code. Click your name or initials (bottom left), then Settings, then Capabilities. Switch on "Code execution
   and file creation".
4. Connect Google. Still in Settings, open Connectors. Find Google Drive and press Connect. Sign in as {google} and
   press Allow. Do the same for Google Sheets and Google Docs.
5. Make a project. In the menu on the left, press Projects, then New project. Call it Invoicing and press Create.
6. Add the rules. In the project, next to Files, press +, then GitHub. Paste this link:
   {repo}
   Untick everything, tick only the folder called workspace, and press Add.
7. Add your instruction. In the project, press Instructions (it may say "Set project instructions"). Paste everything
   between the two lines below, exactly as it is, and press Save.
   ----------
{instruction}
   ----------
8. Test it. Start a new chat in the project and type: Who do you work for?
   It should answer {name}, coach {number}, and your folder {folder}, and say it can't open hub. Send {head} a copy
   of its answer.

That's it. Each month, open a new chat in the Invoicing project and say, for example, "Do my November invoices".
On your phone: open the Claude app, then Projects, then Invoicing.
If Claude ever says "System update ready": next time you're at a computer, open the project, find coaching-crm under
Files, and press Sync.

## unshare

Remove {first}'s access. It takes about 3 minutes, on a computer. Access given to a folder inside another has to be
removed from that folder too, so there are five folders to do.

{first}'s Google account: {google}

1. Go to drive.google.com, signed in as yourself, and open the business's folder.
2. Double-click {folder} to open it.
3. Right-click invoice-lists, then Share, then Share. Next to {google}, open the access menu, choose Remove access,
   and press Save.
4. Do the same for invoices, and then for pops.
5. Go back to the business's folder. Do the same for {folder} itself, and then for factory.
6. Come back here and say "done".

{first}'s Claude can no longer open anything. Their folder and their invoices stay, and payments for those invoices are
still matched by the bank recon.
