# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Convert hOCR files (from Google Document AI) to plaintext.

import csv
import os
import re


def read_pages():
    pages = {}
    with open('src/pages.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date = row["Date"]
            page_id, page_label = int(row["PageID"]), row["PageLabel"]
            pages.setdefault(date, []).append((page_id, page_label))
    return pages


MIN_Y = {
    29210065: 1600,
}

def convert_page(date, page_id, page_label):
    boxes = []
    min_y = MIN_Y.get(page_id, 260)
    print(f"# Date: {date} Page: {page_id}/{page_label}")
    with open(f"hocr/{page_id}.hocr", "r") as f:
        hocr = f.read()
    for x, y, x2, y2, txt in re.findall(
        r"<span class='ocr_line' id='line_[_0-9]+' title='bbox (\d+) (\d+) (\d+) (\d+)'>(.+)\n", hocr):
        x, y = int(x), int(y)
        w, h = int(x2) - x, int(y2) - y
        if y < min_y:
            continue
        if txt == "-":
            continue
        if re.match(r"^-\w", txt):
            txt = "- " + txt[1:]
        boxes.append((x, y, w, h, txt))
    for x, y, w, h, txt in boxes:
        print(f"{txt}  # {x},{y},{w},{h}")


if __name__ == "__main__":
    for date, pages in sorted(read_pages().items()):
        for page_id, page_label in pages:
            convert_page(date, page_id, page_label)
        break
