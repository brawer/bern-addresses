# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Internal utility functions.

from collections import namedtuple
import csv
from dataclasses import dataclass
import os
from pathlib import Path
import re
import urllib.request


Page = namedtuple("Page", "id date is_title_page")


@dataclass
class Box:
    x: int
    y: int
    width: int
    height: int

    def union(self, other: "Box") -> "Box":
        """
        Returns the union of this box with another box.
        """
        x1 = min(self.x, other.x)
        x2 = max(self.x + self.width, other.x + other.width)
        y1 = min(self.y, other.y)
        y2 = max(self.y + self.height, other.y + other.height)
        x1, y1 = min(x1, x2), min(y1, y2)
        x2, y2 = max(x1, x2), max(y1, y2)
        return Box(x1, y1, x2 - x1, y2 - y1)


@dataclass
class OCRLine:
    page_id: int
    column: int
    text: str
    box: Box


@dataclass
class AddressBookEntry:
    id: int | None
    page_id: int
    box: Box
    family_name: str
    given_name: str
    maiden_name: str
    nobility_name: str
    title: str
    occupations: list[str]
    addresses: list[str]
    workplace: str
    unrecognized: str

    def to_dict(self) -> dict[str, str]:
        """
        Returns a dictionary on behalf of older parts of the codebase,
        such as the validator in src/validator.py.
        """
        pos = f"{self.box.x},{self.box.y},{self.box.width},{self.box.height}"
        occ_1 = self.occupations[0] if len(self.occupations) >= 1 else ""
        occ_2 = self.occupations[1] if len(self.occupations) >= 2 else ""
        occ_3 = self.occupations[2] if len(self.occupations) >= 3 else ""
        addr_1 = self.addresses[0] if len(self.addresses) >= 1 else ""
        addr_2 = self.addresses[1] if len(self.addresses) >= 1 else ""
        addr_3 = self.addresses[2] if len(self.addresses) >= 1 else ""
        return {
            "ID": f"BAE-{self.id}" if self.id else "",
            "Scan": str(self.page_id),
            "Position": pos,
            "Name": self.family_name,
            "Vorname": self.given_name,
            "Ledigname": self.maiden_name,
            "Adelsname": self.nobility_name,
            "Titel": self.title,
            "Beruf": occ_1,
            "Beruf 2": occ_2,
            "Beruf 3": occ_3,
            "Adresse": addr_1,
            "Adresse 2": addr_2,
            "Adresse 3": addr_3,
            "Arbeitsort": self.workplace,
            "nicht zuweisbar": self.unrecognized,
        }


def fetch_jpeg(page_id: int) -> Path:
    """
    Fetch the JPEG image for a single page from e-rara.ch.

    If the image is already in cache, the cached content is returned
    without re-downloading it over the internet.

    Args:
        page_id: Numeric ID of the page, such as 29210874
        for https://www.e-rara.ch/bes_1/periodical/pageview/29210874.

    Returns:
        Path to the fetched JPEG file on local disk.
    """
    filepath = os.path.join("cache", "images", f"{page_id}.jpg")
    if not os.path.exists(filepath):
        os.makedirs(os.path.join("cache", "images"), exist_ok=True)
        url = f"https://www.e-rara.ch/download/webcache/2000/{page_id}"
        with urllib.request.urlopen(url) as u:
            img = u.read()
        # Write to a temp file, followed by (atomic) rename, so we never
        # have partially written files in the final location, even if
        # the process crashes while writing out the file.
        with open(filepath + ".tmp", "wb") as f:
            f.write(img)
        os.rename(filepath + ".tmp", filepath)
    return Path(filepath)


def parse_pages(pages: str) -> set[int]:
    """
    Parse the string passed as the --pages command-line argument.

    Args:
        pages: A string designating a set of pages, for example
               "29210355,29210410-29210412".

    Returns:
        A set of integer page IDs, such as
        {29210355, 29210410, 29210355, 29210411, 29210355, 29210412}.
    """
    result = set()
    if not pages:
        return result
    for s in pages.split(","):
        s = s.strip()
        if "-" in s:
            if m := re.match(r"(\d+)\-(\d+)", s):
                for page_id in range(int(m.group(1)), int(m.group(2)) + 1):
                    result.add(page_id)
            else:
                raise ValueError(f"not in YYYY-YYYY format: {s}")
        else:
            result.add(int(s))
    return result


def parse_years(years: str) -> set[int]:
    """
    Parse the string passed as the --years command-line argument.

    Args:
        years: A string designating a set of years, for example
               "1880-1883,1905".

    Returns:
        A set of integer years, such as {1880, 1881, 1882, 1883, 1905}.
    """
    result = set()
    if not years:
        return result
    for s in years.split(","):
        s = s.strip()
        if "-" in s:
            if m := re.match(r"(\d{4})\-(\d{4})", s):
                for year in range(int(m.group(1)), int(m.group(2)) + 1):
                    result.add(year)
            else:
                raise ValueError(f"not in YYYY-YYYY format: {s}")
        else:
            result.add(int(s))
    return result


def read_pages() -> dict[str, list[Page]]:
    path = Path(__file__) / ".." / "pages.csv"
    pages = {}
    seen_dates: set[str] = set()
    with open(path.resolve()) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date, page_id = row["Date"], int(row["PageID"])
            is_title_page = date not in seen_dates
            seen_dates.add(date)
            p = Page(page_id, date, is_title_page)
            pages.setdefault(date, []).append(p)
    return pages


def read_ocr_lines(volume: str) -> list[OCRLine]:
    lines = []
    path = Path(__file__) / ".." / ".." / "ocr-lines" / f"{volume}.csv"
    with open(path.resolve(), "r") as fp:
        for row in csv.DictReader(fp):
            box = Box(
                x=int(row["X"]),
                y=int(row["Y"]),
                width=int(row["Width"]),
                height=int(row["Height"]),
            )
            line = OCRLine(
                page_id=int(row["PageID"]),
                column=int(row["Column"]),
                box=box,
                text=row["Text"],
            )
            lines.append(line)
    return lines


def test_addressbookentry_to_dict():
    entry = AddressBookEntry(
        id=42,
        page_id=3010970,
        box=Box(302, 1091, 405, 23),
        family_name="Meier",
        given_name="Anna",
        maiden_name="Müller",
        nobility_name="von Mülinen",
        title="Dr.",
        occupations=["Fabrikantin", "O2", "O3"],
        addresses=["A-Str. 1", "B-Str. 2", "C-Str. 3"],
        workplace="Müller & Co.",
        unrecognized="Huh?",
    )
    assert entry.to_dict() == {
        "ID": "BAE-42",
        "Scan": "3010970",
        "Position": "302,1091,405,23",
        "Name": "Meier",
        "Vorname": "Anna",
        "Ledigname": "Müller",
        "Adelsname": "von Mülinen",
        "Titel": "Dr.",
        "Beruf": "Fabrikantin",
        "Beruf 2": "O2",
        "Beruf 3": "O3",
        "Adresse": "A-Str. 1",
        "Adresse 2": "B-Str. 2",
        "Adresse 3": "C-Str. 3",
        "Arbeitsort": "Müller & Co.",
        "nicht zuweisbar": "Huh?",
    }


def test_box_union():
    a = Box(1, 5, 2, 6)
    assert a.union(Box(7, 3, 11, 3)) == Box(1, 3, 17, 8)


def test_read_ocr_lines():
    lines = read_ocr_lines("1864-08-15")
    line = lines[1]
    assert line.page_id == 29210592
    assert line.column == 1
    assert line.box == Box(287, 1632, 601, 56)
    assert line.text == "Abderhalden A. Näh., Ag. 33"
