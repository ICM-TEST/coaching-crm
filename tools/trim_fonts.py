#!/usr/bin/env python3
"""Trim the Inter font files for invoices: Latin characters only, no screen hinting.

  python3 tools/trim_fonts.py <folder with Inter-Regular/Medium/SemiBold/Bold.ttf from the official release>

Writes the trimmed files into _templates/drive/factory/invoice-template/fonts/. A printed or PDF invoice looks the
same; each invoice PDF is about half the size. Needs fontTools. Inter is under the SIL Open Font License, which
allows this.
"""
import sys
from pathlib import Path

from fontTools import subset

OUT = Path(__file__).resolve().parent.parent / "workspace" / "_templates" / "drive" / "factory" / "invoice-template" / "fonts"
UNICODES = "U+0020-007E,U+00A0-00FF,U+2013-2014,U+2018-201D,U+2022,U+2026,U+20AC"

for weight in ("Regular", "Medium", "SemiBold", "Bold"):
    src = Path(sys.argv[1]) / f"Inter-{weight}.ttf"
    options = subset.Options()
    options.hinting = False                 # screen hinting: no use in a PDF
    options.layout_features = []            # the invoice uses no ligatures or alternates
    options.name_IDs = ["*"]
    font = subset.load_font(str(src), options)
    sub = subset.Subsetter(options)
    sub.populate(unicodes=subset.parse_unicodes(UNICODES))
    sub.subset(font)
    subset.save_font(font, str(OUT / src.name), options)
    print(f"{src.name}: {src.stat().st_size:,} → {(OUT / src.name).stat().st_size:,} bytes")
