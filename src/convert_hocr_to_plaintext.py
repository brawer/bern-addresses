# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Convert hOCR files (from Google Document AI) to plaintext.

import csv
import os
import re


# lines longer than this, featuring '|', have
# been greedy matched by ocr, so we split them
LINE_WIDTH_THRESHOLD = 200

def read_pages():
    pages = {}
    with open('src/pages.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date = row["Date"]
            page_id, page_label = int(row["PageID"]), row["PageLabel"]
            pages.setdefault(date, []).append((page_id, page_label))
    return pages


# If any of these words are last on a line, we join that line with the next one,
# unless the following line starts with a hyphen (that got actually recognized
# by OCR). The heuristic is not perfect but seems to work pretty well.
JOIN_WORDS = {
    'am',
    'an',
    'auf',
    'bei',
    'beim',
    'd.',
    'dem',
    'den',
    'der',
    'des',
    'eidg.',
    'für',
    'im',
    'in',
    'kant.',
    'städt.',
    'u.',
    'um',
    'und',
}


# Abbreviations (and full words) that are definitely not family names.
# If they start a new line, we assume that OCR has missed to recognize
# a leading hyphen, and insert that missing hyphen programmatically.
ABBREVS = {
    '&',
    '& Co',
    'Abl.',
    'Alb.',
    'Chr.',
    'Cie.',
    'Fr.',
    'Frau',
    'Frl.',
    'gb.',
    'geb.',
    'Gebr.'
    'Gottf.',
    'Math.',
    'Karol.',
    'Jb.',
    'Jh.',
    'Jgfr.',
    'Joh.',
    'Pfr.',
    'Sam.',
    'Schn.',
    'Schuhm.',
    'Schwest.',
    'Tel.',
    'Th.',
    'Wittwe',
    'Wtw.',
    'Wwe.',
}

def read_page(date, page_id):
    has_phone_arrows = (date >= '1885') and (date <= '1924')
    boxes = []
    min_y = 260
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
            if has_phone_arrows:
                txt = re.sub(r'(#)\d{3,}', '↯', txt)
            txt = txt.replace('#', ' ')
        txt = txt.replace('ſ', 's').replace("'", "’")
        if has_phone_arrows:
            txt = re.sub(r'\s+(\d{4,})[^\]]', r' ↯\1 ', txt)
        if txt.strip() == '↯':
            continue
        if w > LINE_WIDTH_THRESHOLD and '|' in txt:
            cols = txt.split('|')
            count = len(cols)
            for i, col in enumerate(cols):
                col = col.strip()
                # mark up lines we're confident
                # that they've been split
                if col.endswith('-'):
                    col += '@@@GLUE@@@'
                if col != '':
                    boxes.append(
                        (int(x + (i * w / count)), y,
                        int(w / count), h,
                        col + '\n'))
        else:
            boxes.append((x, y, w, h, txt))
    for x, y, w, h, txt in boxes:
        yield f"{txt}  # {x},{y},{w},{h}"


def convert_page(date, page_id, page_label):
    yield f"# Date: {date} Page: {page_id}/{page_label}"
    last, last_pos = '', ''
    for line in read_page(date, page_id):
        line = ' '.join(line.replace('.', '. ').split())
        line = line.replace('. ,', '.,').replace('. -', '.-').replace('. )', '.)').replace('. :', '.:')
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
        # TODO(random-ao): worth moving to fix_conjunctions.py?
        if last.endswith('-'):
            last = last[:-1] + cur
            last_pos += ';' + cur_pos
        elif any(last.endswith(' ' + x) for x in JOIN_WORDS) and not cur.startswith('-'):
            last = last + ' ' + cur
            last_pos += ';' + cur_pos
        elif line.startswith('u.') and not any(x in line for x in ['Comp', 'Cie']):
            last = last + ' ' + cur
            if last_pos != '':
                last_pos += ';' + cur_pos
            else:
                last_pos = cur_pos
        else:
            if last or last_pos: yield f'{last}  # {last_pos}'
            last, last_pos = cur, cur_pos
    if last or last_pos: yield f'{last}  # {last_pos}'


if __name__ == "__main__":
    for date, pages in sorted(read_pages().items()):
        if date <= '1862': continue

        env_vl = os.environ.get('PROCESS_VOLUMES', False)
        if env_vl:
            vl = env_vl.split(',')
            if date not in vl:
                continue

        print('Converting %s' % date)
        with open(f'proofread/{date}.txt', 'w') as out:
            for page_id, page_label in pages:
                for line in convert_page(date, page_id, page_label):
                    out.write(line + '\n')


