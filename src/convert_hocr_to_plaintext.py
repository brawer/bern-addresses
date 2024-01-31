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

JOIN_WORDS = {
    'in', 'im', 'auf', 'bei', 'beim', 'der', 'des', 'den', 'um', 'am', 'an',
}


ABBREVS = {
    'Chr.', 'Jb.', 'Th.', 'Fr.', 'Frl.', 'Wtw.', 'Wwe.', 'Schwest.', 'Pfr.', 'Gebr.',
}

def read_page(date, page_id):
    boxes = []
    min_y = MIN_Y.get(page_id, 260)
    with open(f"cache/hocr/{page_id}.hocr", "r") as f:
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
        if '#' in txt:
            txt = txt.replace('#', ' ')
        txt = txt.replace('ſ', 's')
        boxes.append((x, y, w, h, txt))
    for x, y, w, h, txt in boxes:
        yield f"{txt}  # {x},{y},{w},{h}"


def convert_page(date, page_id, page_label):
    yield f"# Date: {date} Page: {page_id}/{page_label}"
    last, last_pos = '', ''
    for line in read_page(date, page_id):
        line = ' '.join(line.replace('.', '. ').split())
        line = line.replace('. ,', '.,').replace('. -', '.-')
        if line[0] == '#':
            if last or last_pos: yield f'{last}  # {last_pos}'
            yield line
            last, last_pos = '', ''
            continue
        if len(line) > 3 and (re.match(r'^[A-Z]\.', line) or any(line.startswith(x) for x in ABBREVS)):
            line = '- ' + line
        if line.startswith('--'):
            line = '- -' + line[2:]
        elif line.startswith('('):
            line = '- ' + line
        cur, cur_pos = [x.strip() for x in line.split('#')]
        if last.endswith('-'):
            last = last[:-1] + cur
            last_pos += ';' + cur_pos
        elif last.endswith(','):
            last = last + ' ' + cur
            last_pos += ';' + cur_pos
        elif any(last.endswith(' ' + x) for x in JOIN_WORDS) and not cur.startswith('-'):
            last = last + ' ' + cur
            last_pos += ';' + cur_pos
        else:
            if last or last_pos: yield f'{last}  # {last_pos}'
            last, last_pos = cur, cur_pos
    if last or last_pos: yield f'{last}  # {last_pos}'


if __name__ == "__main__":
    for date, pages in sorted(read_pages().items()):
        if not date.startswith('1861'): continue
        for page_id, page_label in pages:
            for line in convert_page(date, page_id, page_label):
                print(line)

