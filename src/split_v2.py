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
    AddressBookEntry,
    Box,
    OCRLine,
    Page,
    fetch_jpeg,
    parse_years,
    read_pages,
    read_ocr_lines,
)
from validator import Validator


REPLACEMENTS = {
    "ẵ": "ä",
    "gaffe": "gasse",
    "I.": "J.",
    "Käshdir": "Käshdlr",
    "Megg": "Metzg",
    "Mezg": "Metzg",
    "Nent": "Rent",
    "Nevifor": "Revisor",
    "plazg": "platzg",
    "plagg": "platzg",
    "Räfich": "Käfich",
    "Regt.": "Negt.",
    "Schlsfr": "Schlssr",
    "Schweft": "Schwest",
}


class Splitter:
    def __init__(self, validator: Validator):
        self.validator = validator

    def split(self, lines: list[OCRLine]) -> list[AddressBookEntry]:
        result: list[AddressBoookEntry] = []
        lemma: str = ""
        for line in merge_lines(lines):
            s = line.text
            name, s = self.split_family_name(s)
            if name == "—":
                name = lemma
            else:
                # After "von Goumoens-von Tavel", the new lemma is "von Goumoens".
                lemma = name.split("-")[0].strip()
        return result

    def split_name(self, text: str) -> (str, str):
        p = text.split(",")
        n = p[0].replace(" -", "-").replace("- ", "-")
        words = n.split()
        pos = 0
        prefixes = {"de", "De", "von", "Von", "v.", "V."}
        if words[0] in prefixes:
            pos = pos + 1
        if any(words[pos].endswith("-" + p) for p in prefixes):
            pos = pos + 1
        words[0] = {
            "De": "de",
            "v.": "von",
            "V.": "von",
        }.get(words[0], words[0])
        name = " ".join(words[: pos + 1])
        if name in "-–—":
            name = "—"
        rest_list = [" ".join(words[pos + 1 :])] + p[1:]
        rest = ", ".join(rp.strip() for rp in rest_list if rp)
        return (name, rest)


def main(years: set[int]) -> None:
    validator = Validator()
    splitter = Splitter(validator)
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
                splitter.split(col_lines)


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


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--years", default="1864", type=parse_years)
    args = ap.parse_args()
    main(years=args.years)
