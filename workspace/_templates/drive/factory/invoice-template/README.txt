Invoice template

The layout is fixed in scripts/issue.py (measured from the business's own invoice), so no coach can change it.

Fonts: fonts/ holds Inter (Regular, Medium, SemiBold, Bold), the font the business's invoices use, from the
official Inter 4.1 release, trimmed for invoices by tools/trim_fonts.py: Latin characters only, no screen hinting.
That keeps each invoice PDF around 40 KB without changing how it looks. Inter is free under the SIL Open Font License
(fonts/OFL-Inter-LICENSE.txt), which allows this. If the files are ever missing, the generator falls back to Helvetica.
