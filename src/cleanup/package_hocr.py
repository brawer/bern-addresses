# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

import csv
import os
import zipfile


# Ad-hoc script for packaging the hOCR files (from send_to_ocr.py)
# into a ZIP archive, separate for each volume.
def package_hocr(zipfilename):
    pages = read_pages()
    with zipfile.ZipFile(zipfilename, "w") as zf:
        for date, pages in pages.items():
            print(date, len(pages))
            for page in pages:
                zf.write(
                    filename=os.path.join("cache", "hocr", f"{page}.hocr"),
                    arcname=f"{date}/{page}.hocr",
                    compress_type=zipfile.ZIP_DEFLATED,
                )


def read_pages():
    pages = {}
    path = os.path.join(os.path.dirname(__file__), "..", "pages.csv")
    with open(path, "r") as fp:
        for row in csv.DictReader(fp):
            date, page = row["Date"], row["PageID"]
            pages.setdefault(date, []).append(page)
    for v in pages.values():
        v.sort(key=int)
    return pages


if __name__ == "__main__":
    package_hocr("hocr.zip")
