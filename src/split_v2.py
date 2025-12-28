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


COMPANY_ABBREVS = {
    "AG",
    "A.-G.",
    "Cie.",
    "Co.",
    "Comp.",
    "Compagnie",
    "Gebr.",
    "Gebrüder",
    "Gebrüd.",
    "& Cie.",
    "& Co.",
    "& Comp.",
    "& Cp.",
    "& Sohn",
    "& Söhne",
    "u. Cie.",
    "u. Comp.",
}


MAIDEN_NAME_PREFIXES = {
    "geb.",
    "gb.",
    "geborne",
    "geborene",
}


NOBILITY_PREFIXES = {
    "de": "de",
    "De": "de",
    "von": "von",
    "Von": "von",
    "v.": "von",
    "V.": "von",
}


class Splitter:
    def __init__(self, validator: Validator):
        self.validator = validator

    def split(self, lines: list[OCRLine]) -> list[AddressBookEntry]:
        result: list[AddressBoookEntry] = []
        lemma: str = ""
        lines = merge_lines(sorted(lines, key=lambda l: l.box.y))
        min_x = min(line.box.x for line in lines)
        max_x = max(line.box.x + line.box.width for line in lines)
        for line in lines:
            name, rest = self.split_name(line.text)
            if name == "—":
                name = lemma
            else:
                # After "von Goumoens-von Tavel", the new lemma is "von Goumoens".
                lemma = name.split("-")[0].strip()
            company, rest = self.split_company(name, rest)
            if company:
                name = company
                maiden_name = ""
                title = "[Firma]"
            else:
                maiden_name, rest = self.split_maiden_name(rest)
                title, rest = self.split_title(rest)

            addresses, rest = self.split_addresses(rest)

            # TODO
            given_name = ""
            occupations = []

            box = Box(
                x=min_x, y=line.box.y, width=max_x - min_x, height=line.box.height
            )
            entry = AddressBookEntry(
                id=None,
                page_id=line.page_id,
                box=box,
                family_name=name,
                given_name=given_name,
                maiden_name=maiden_name,
                nobility_name="",
                title=title,
                occupations=occupations,
                addresses=addresses,
                workplace="",
                unrecognized=rest,
            )
            result.append(entry)
        return result

    def split_name(self, text: str) -> (str, str):
        p = text.split(",")
        n = p[0].replace(" -", "-").replace("- ", "-")
        words = n.split()
        pos = 0
        if words[0] in NOBILITY_PREFIXES:
            pos = pos + 1
        if any(words[pos].endswith("-" + p) for p in NOBILITY_PREFIXES):
            pos = pos + 1
        words[0] = NOBILITY_PREFIXES.get(words[0], words[0])
        name = " ".join(words[: pos + 1])
        if name in "-–—":
            name = "—"
        rest_list = [" ".join(words[pos + 1 :])] + p[1:]
        rest = ", ".join(rp.strip() for rp in rest_list if rp)
        return (name, rest)

    def split_company(self, name: str, rest: str) -> (str, str):
        words = rest.split()
        for a in COMPANY_ABBREVS:
            if rest.startswith(a):
                company = f"{name} {a}"
                rest = rest.removeprefix(a).removeprefix(",").strip()
                return company, rest
        return "", rest

    def split_maiden_name(self, text: str) -> (str, str):
        if not any(text.startswith(p) for p in MAIDEN_NAME_PREFIXES):
            return "", text
        parts = text.split(",")
        words = parts[0].split()[1:]
        maiden_name, rest_words = words[0], words[1:]
        if len(words) >= 2:
            if nob := NOBILITY_PREFIXES.get(words[0]):
                maiden_name, rest_words = nob + " " + words[1], words[2:]
        p = [" ".join(rest_words)] + parts[1:] if rest_words else parts[1:]
        rest = ", ".join([x.strip() for x in p])
        return (maiden_name, rest)

    def split_title(self, text: str) -> (str, str):
        for title in self.validator.titles:
            if text.startswith(title):
                rest = text.removeprefix(title).strip().removeprefix(",").strip()
                return (title, rest)
        return ("", text)

    def split_addresses(self, text: str) -> (list[str], str):
        p = [p.strip() for p in text.split(",")]
        if len(p) == 0:
            return [], text
        addrs = self.cleanup_address(p[0])
        if len(addrs) > 0:
            p = p[1:]
        if len(p) > 0:
            final_addrs = self.cleanup_address(p[-1])
            if final_addrs:
                p = p[:-1]
                addrs.extend(final_addrs)
        return addrs, ", ".join(p)

    def cleanup_address(self, addr: str) -> list[str]:
        val = self.validator
        is_street = lambda s: (s in val.street_abbrevs) or (s in val.streets)
        if addr in val.pois:
            return [addr]
        if m := re.match(r"^(.+) (\d+[a-t]?)$", addr):
            street, num = m.groups()
            if is_street(street):
                return [f"{street} {num}"]
        if m := re.match(r"^(.+) (\d+[a-t]?) (u\.|und) (\d+[a-t]?)$", addr):
            street, num1, _und, num2 = m.groups()
            if is_street(street):
                return [f"{street} {num1}", f"{street} {num2}"]
        if m := re.match(r"^(.+) (\d+[a-t]?) (u\.|und) (.+) (\d+[a-t]?)$", addr):
            s1, num1, _und, s2, num2 = m.groups()
            if is_street(s1) and is_street(s2):
                return [f"{s1} {num1}", f"{s2} {num2}"]
        if m := re.match(r"^(.+) (\d+[a-t]?) (u\.|und) (.+)$", addr):
            s1, num1, _und, poi = m.groups()
            if is_street(s1) and poi in val.pois:
                return [f"{s1} {num1}", poi]
        return []


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
                for entry in splitter.split(col_lines):
                    print(entry)


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
