# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Tool for splitting 1822 scans into Excel sheets for huamn review.
# The 1822 address book has a very different format from other years,
# so we use a dedicated tool for splitting it.

import os
import re

import cv2
import numpy

from utils import fetch_jpeg
from validator import Validator


COMPANY_WORDS = {
    "Comp.",
    "Buereau",
    "Büreau",
    " und ",
}


def read_1822(validator):
    path = os.path.join(os.path.dirname(__file__), "..", "proofread", "1822-02-01.txt")
    pattern = re.compile(r" [A-Za-z0-9\-]+:")
    date, category, isco, noga = "", "", "", ""
    page_id, page_no = None, None
    with open(path) as fp:
        for line in fp.readlines():
            line = line.strip()
            if line[0] == "#":
                g = pattern.sub(lambda g: "|" + g.group(0), line)
                d = {}
                for c in [w.strip() for w in g.split("|") if w != "#"]:
                    key, value = c.split(" ", 1)
                    d[key] = value
                if any(k in d for k in ("NOGA-2008:", "CH-ISCO-19:", "Category:")):
                    category, isco, noga = "", "", ""
                for key, value in d.items():
                    if key == "Date:":
                        date = value
                    elif key == "Page:":
                        page_id, page_no = [int(x) for x in value.split("/")]
                        margin_left, margin_right = detect_margins(page_id)
                    elif key == "Category:":
                        category = value
                    elif key == "CH-ISCO-19:":
                        isco = str(int(value))
                    elif key == "NOGA-2008:":
                        noga = str(int(value))
                    else:
                        assert False, f'unexpected key "{key}"'
                continue
            text, position = line.split("#")
            text = text.replace("  ", " ")
            position = position.strip()

            remarks = ""
            if p := re.search(r"\((.+)\)", line):
                remarks = p.group(1).removesuffix(",")

            no_parens = re.sub(r"\(.+\),?", "", text).replace("  ", " ")
            parts = [p.strip() for p in no_parens.split(",")]
            address = parts[-1].removesuffix(".")
            parts = parts[:-1]

            title = ""
            if parts and parts[-1] in validator.titles:
                title = parts[-1]
                parts = parts[:-1]
            elif parts and parts[0] in validator.titles:
                title = parts[0]
                parts = parts[1:]

            maidenname = ""
            if parts and parts[-1].startswith("geb."):
                maidenname = parts[-1].removeprefix("geb.").strip()
                parts = parts[:-1]
            elif parts and parts[-1].startswith("geborne "):
                maidenname = parts[-1].removeprefix("geborne").strip()
                parts = parts[:-1]

            address_2 = ""
            if parts and parts[-1] in validator.pois:
                address_2 = parts[-1]
                parts = parts[:-1]

            occupation = category
            if len(parts) == 4 and parts[2] in ("Wirth", "Wirthin"):
                occ = parts[2] + " " + parts[3]
                occ = occ.replace(" Zu ", " zu ").replace(" Zum ", " zum ")
                occupation = occ
                parts = parts[:-2]

            name = parts[0] if parts else ""
            if any(w in " ".join(parts) for w in COMPANY_WORDS):
                assert title == "", text
                title = "[Firma]"
                name = ", ".join(parts).replace(", und Comp.", " und Comp.")
                parts = []
            else:
                parts = parts[1:]

            given_name = ""
            if (
                parts
                and title != "[Firma]"
                and all(p in validator.given_names for p in parts[0].split())
            ):
                given_name = parts[0]
                parts = parts[1:]

            if parts:
                remarks = ", ".join([x for x in [remarks] + parts if x])

            entry = {
                "Scan": str(page_id),
                "ID": simplify_position(position, margin_left, margin_right),
                "Name": name,
                "Vorname": given_name,
                "Ledigname": maidenname,
                "Adelsname": "",
                "Adresse": address,
                "Adresse 2": address_2,
                "Adresse 3": "",
                "Bemerkungen": remarks,
                "Titel": title,
                "Beruf": category,
                "Beruf 2": "",
                "Beruf 3": "",
                "Bemerkungen": remarks,
            }
            yield entry


def detect_margins(page_id):
    image = fetch_jpeg(page_id)
    page = numpy.asarray(image)
    blurred = cv2.bilateralFilter(page, 9, 75, 75)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    w, h = bw.shape[1], bw.shape[0]
    cv2.rectangle(bw, (0, 0), (150, h - 1), color=255, thickness=-1)
    cv2.rectangle(bw, (w - 150, 0), (w - 1, h - 1), color=255, thickness=-1)
    cv2.rectangle(bw, (0, 0), (w - 1, 150), color=255, thickness=-1)
    cv2.rectangle(bw, (0, h - 150), (w - 1, h - 1), color=255, thickness=-1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 180))
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, 3)
    for left in range(350):
        if numpy.count_nonzero(bw[:, left]) < bw.shape[0] - 80:
            break
    if left > 5:
        left -= 5
    for right in range(bw.shape[1] - 1, bw.shape[1] - 350, -1):
        if numpy.count_nonzero(bw[:, right]) < bw.shape[0] - 80:
            break
    if False:
        cv2.rectangle(
            blurred, (left, 0), (right, h - 1), color=(0, 0, 255), thickness=4
        )
        cv2.imwrite(f"{page_id}.png", blurred)
    return (left, right)


def simplify_position(position, margin_left, margin_right):
    min_y, max_y = None, None
    for pos in [p.split(",") for p in position.split(";")]:
        x, y, w, h = [int(i) for i in pos]
        min_y = min(y, min_y) if min_y else y
        max_y = max(y, max_y) if max_y else y
    assert min_y != None and max_y != None
    w = margin_right - margin_left
    h = max_y = min_y
    return f"{margin_left},{min_y},{w},{h}"


if __name__ == "__main__":
    val = Validator()
    for line, entry in enumerate(read_1822(val)):
        # print(entry)
        addr = entry["Adresse"].rsplit(" ", 1)[0]
        if False and "ß" in addr:
            ss = addr.replace("ß", "ss")
            if ss in val.streets:
                print(",".join([addr, ss]))
        val.validate(entry, ("1822-02-01.txt", line + 1))
    val.report()
