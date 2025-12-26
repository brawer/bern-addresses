# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Usage:
#
#     venv/bin/python3 src/split_v2.py --years=1870-1878

from argparse import ArgumentParser
import csv
from dataclasses import dataclass
from pathlib import Path
import re

from utils import (
    Box,
    OCRLine,
    Page,
    fetch_jpeg,
    parse_years,
    read_pages,
    read_ocr_lines,
)


REPLACEMENTS = {
    "ẵ": "ä",
    "gaffe": "gasse",
    "I.": "J.",
    "Käshdir": "Käshdlr",
    "Megg": "Metzg",
    "Mezg": "Metzg",
    "Nent": "Rent",
    "plazg": "platzg",
    "plagg": "platzg",
    "Räfich": "Käfich",
    "Regt.": "Negt.",
    "Schlsfr": "Schlssr",
}


def main(years: set[int]) -> None:
    for volume, volume_pages in sorted(read_pages().items()):
        year = int(volume[:4])
        if year not in years:
            continue
        ocr_lines = read_ocr_lines(volume)
        for page in volume_pages:
            volume_lines = [l for l in ocr_lines if l.page_id == page.id]
            columns = sorted(set(l.column for l in volume_lines))
            for col in columns:
                col_lines = [l for l in volume_lines if l.column == col]
                for line in merge_lines(col_lines):
                    print(line)
            return


def merge_lines(lines: list[OCRLine]) -> list[OCRLine]:
    result: list[OCRLine] = []
    if len(lines) == 0:
        return result

    assert all(l.page_id == lines[0].page_id for l in lines)
    assert all(l.column == lines[0].column for l in lines)
    column_x = min(l.box.x for l in lines)
    last = None
    for line in lines:
        last = result[-1] if len(result) > 0 else None
        x = line.box.x - column_x
        text = cleanup_text(line.text)
        if x > 200 and re.match(r"^[A-Z]\.$", line.text):
            continue
        if x < 70 or last is None:
            result.append(
                OCRLine(
                    page_id=line.page_id, column=line.column, text=text, box=line.box
                )
            )
            continue
        last_text = last.text
        if any(last_text.endswith(c) for c in "⸗-="):
            text = last_text[:-1] + text
        else:
            text = " ".join((last_text + " " + text).split())
        box = last.box.union(line.box)
        merged = OCRLine(page_id=line.page_id, column=line.column, text=text, box=box)
        result[-1] = merged
    return result


def cleanup_text(s: str) -> str:
    if s[-1] in ":=":
        s = s[:-1] + "-"
    s = s.replace("ſ", "s").replace("ß", "ss").replace("⸗", "-")
    s = re.sub(r"\.([0-9A-ZÄÖÜ])", lambda m: ". " + m.group(1), s)
    s = re.sub(r"([0-9] [a-z][,.]?)", lambda m: m.group(1).replace(" ", ""), s)

    for a, b in REPLACEMENTS.items():
        s = s.replace(a, b)
    return s


def test_cleanup_text():
    assert cleanup_text("ſtraß⸗") == "strass-"
    assert cleanup_text("Aarberger:") == "Aarberger-"
    assert cleanup_text("Aarberger=") == "Aarberger-"
    assert cleanup_text("Räfichgaffe 8 b") == "Käfichgasse 8b"
    assert cleanup_text("Mtzg. 8 b u. 9") == "Mtzg. 8b u. 9"


def test_merge_lines():
    assert merge_lines([]) == []
    lines = [
        OCRLine(29210592, 1, "Adam, Wittwe, Schneiderin,", Box(284, 1963, 628, 54)),
        OCRLine(29210592, 1, "Aarberg. 63", Box(381, 2011, 254, 52)),
        OCRLine(29210592, 1, "— Schweſt., Schneiderinnen,", Box(309, 2066, 604, 45)),
        OCRLine(29210592, 1, "Marktgaſſe 83.", Box(381, 2105, 301, 52)),
        OCRLine(29210592, 1, "Adamina Jean, Lehrer, Poſt⸗", Box(283, 2149, 631, 62)),
        OCRLine(29210592, 1, "gaſſe 44", Box(380, 2204, 170, 47)),
    ]
    assert merge_lines(lines) == [
        OCRLine(
            29210592,
            1,
            "Adam, Wittwe, Schneiderin, Aarberg. 63",
            Box(284, 1963, 628, 100),
        ),
        OCRLine(
            29210592,
            1,
            "— Schwest., Schneiderinnen, Marktgasse 83.",
            Box(309, 2066, 604, 91),
        ),
        OCRLine(
            29210592, 1, "Adamina Jean, Lehrer, Postgasse 44", Box(283, 2149, 631, 102)
        ),
    ]


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--years", default="1864", type=parse_years)
    args = ap.parse_args()
    main(years=args.years)
