# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

import zipfile

# Ad-hoc script for extracting the hOCR files (from send_to_ocr.py)
# of one address book volume into a ZIP archive.
date = "1885-12-15"
pages = [p.split(",")[1] for p in open("src/pages.csv") if p.startswith(date)]
with zipfile.ZipFile("1885-12-15.hocr.zip", "w") as zf:
    for page in pages:
        filename = "hocr/" + page + ".hocr"
        zf.write(
            filename="cache/" + filename,
            arcname=filename,
            compress_type=zipfile.ZIP_DEFLATED,
        )
