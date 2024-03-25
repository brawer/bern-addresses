# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

import csv
import io
import os
import re
import urllib.request
import zipfile

import openpyxl
import PIL


FAMILY_NAMES = {
    line.strip()
    for line in open(os.path.join(os.path.dirname(__file__), "family_names.txt"))
}


GIVEN_NAMES = {
    line.strip()
    for line in open(os.path.join(os.path.dirname(__file__), "givennames.txt"))
}


GIVEN_NAME_ABBREVS = {
    line.strip()
    for line in open(
        os.path.join(os.path.dirname(__file__), "given_name_abbreviations.csv")
    )
    if line != "Abbreviations\n"
}


def read_titles():
    result = set()
    filepath = os.path.join(os.path.dirname(__file__), "titles.csv")
    with open(filepath) as stream:
        for row in csv.DictReader(stream):
            result.add(row["Title"])
    return result


def read_occupations():
    occ = {}
    filepath = os.path.join(os.path.dirname(__file__), "occupations.csv")
    with open(filepath) as stream:
        for row in csv.DictReader(stream):
            occ[row["Occupation"]] = row["CH-ISCO-19"]
    return occ


def read_streets():
    result = set()
    filepath = os.path.join(os.path.dirname(__file__), "streets.csv")
    with open(filepath) as stream:
        for row in csv.DictReader(stream):
            result.add(row["Street"])
    return result


def read_street_abbrevs(streets):
    result = {}
    filepath = os.path.join(os.path.dirname(__file__), "street_abbrevs.csv")
    with open(filepath) as stream:
        for row in csv.DictReader(stream):
            s = row["Street"]
            assert s in streets, f"not in streets.csv: {s}"
            result[row["Abbreviation"]] = s
    return result


def read_pois():
    result = set()
    filepath = os.path.join(os.path.dirname(__file__), "pois.csv")
    with open(filepath) as stream:
        for row in csv.DictReader(stream):
            result.add(row["PointOfInterest"])
    return result


TITLES = read_titles()
OCCUPATIONS = read_occupations()
POIS = read_pois()
STREETS = read_streets()
STREET_ABBREVS = read_street_abbrevs(STREETS)


def is_valid_address(addr):
    if m := re.match(r"^(.+) (\d+[a-t]?)$", addr):
        street, num = m.groups()
        return (street in STREET_ABBREVS) or (street in STREETS)
    if addr in POIS:
        return True
    return False


def split(vol):
    outpath = os.path.basename(vol).split(".")[0] + ".zip"
    zip_file = zipfile.ZipFile(outpath, "w")
    font = openpyxl.styles.Font(name="Calibri")
    red = openpyxl.styles.colors.Color(rgb="00FF2222")
    light_red = openpyxl.styles.colors.Color(rgb="00FFAAAA")
    red_fill = openpyxl.styles.fills.PatternFill(patternType="solid", fgColor=red)
    light_red_fill = openpyxl.styles.fills.PatternFill(
        patternType="solid", fgColor=light_red
    )
    page_re = re.compile(r"^# Date: (\d{4}-\d{2}-\d{2}) Page: (\d+)/(.*)")
    sheet, date, page_id, lemma, name, row = None, None, None, "-", "", 0
    workbook, image = None, None
    for line in open(vol):
        line = line.strip()
        if m := page_re.match(line):
            save_workbook(workbook, page_id, zip_file)
            date, page_id, page_num = m.groups()
            workbook = openpyxl.Workbook()
            del workbook["Sheet"]
            sheet = create_sheet(workbook, page_id, page_num)
            row = 2
            image = fetch_jpeg(page_id)
            continue
        p, pos = line.split("#", 1)
        pos = ",".join([str(x) for x in simplify_pos(pos)])
        p = [x.strip() for x in p.split(",")]
        p = [x for x in p if x != ""]
        if p[0].startswith("-"):
            p[0] = lemma + " " + p[0][1:].strip()
        name, rest = split_family_name(p[0])
        # After "von Goumoens-von Tavel", the new lemma is "von Goumoens".
        lemma = name.split("-")[0].strip()
        maidenname, rest = split_maidenname(rest)
        p = [rest] + p[1:] if rest else p[1:]
        title, p = split_title(p)
        address, address2, p = split_address(p)
        givenname, p = split_givenname(p)
        occupation, p = split_occupation(p)
        other = ", ".join(p)
        row = row + 1

        family_name_ok = name in FAMILY_NAMES
        given_name_ok = all(
            n in GIVEN_NAMES or n in GIVEN_NAME_ABBREVS for n in givenname.split()
        )
        maiden_name_ok = (not maidenname) or (maidenname in FAMILY_NAMES)
        title_ok = (not title) or (title in TITLES)
        occupation_ok = (not occupation) or (occupation in OCCUPATIONS)
        address_ok = (not address) or is_valid_address(address)
        address2_ok = (not address2) or is_valid_address(address2)
        other_ok = not other
        all_ok = (
            family_name_ok
            and given_name_ok
            and maiden_name_ok
            and title_ok
            and occupation_ok
            and address_ok
            and address2_ok
            and other_ok
        )

        # id
        cell = sheet.cell(row, 1)
        cell.value, cell.font = pos, font
        if not all_ok:
            cell.fill = light_red_fill

        # scan
        cell = sheet.cell(row, 2)
        cell.value, cell.font = "", font
        if not all_ok:
            cell.fill = light_red_fill
        cropped = crop_image(image, pos)
        sheet.add_image(cropped, f"B{row}")
        sheet.row_dimensions[row].height = cropped.height + 5

        # family name
        cell = sheet.cell(row, 3)
        cell.value, cell.font = name, font
        if not family_name_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # given name
        cell = sheet.cell(row, 4)
        cell.value, cell.font = givenname, font
        if not given_name_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # maiden name
        cell = sheet.cell(row, 5)
        cell.value, cell.font = maidenname, font
        if not maiden_name_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # title
        cell = sheet.cell(row, 6)
        cell.value, cell.font = title, font
        if not title_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # occupation
        cell = sheet.cell(row, 7)
        cell.value, cell.font = occupation, font
        if not occupation_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # address
        cell = sheet.cell(row, 8)
        cell.value, cell.font = address, font
        if not address_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # address2
        cell = sheet.cell(row, 9)
        cell.value, cell.font = address2, font
        if not address2_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill

        # other
        cell = sheet.cell(row, 10)
        cell.value, cell.font = other, font
        if not other_ok:
            cell.fill = red_fill
        elif not all_ok:
            cell.fill = light_red_fill
    save_workbook(workbook, page_id, zip_file)
    # outpath = os.path.basename(vol).split(".")[0] + ".xlsx"
    # workbook.save(outpath)
    zip_file.close()


def save_workbook(workbook, page_id, zip_file):
    if workbook is not None:
        # TODO: Remove this check. Just for sending a small initial sample.
        if int(page_id) >= 29210075:
            return
        workbook.save("tmp.xlsx")
        with open("tmp.xlsx", "rb") as f:
            content = f.read()
        zip_file.writestr(
            f"{page_id}.xlsx",
            content,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )


def split_family_name(n):
    n = n.replace(" - ", "-")
    words = n.split()
    if words[0] in {"de", "De"}:
        return ("de " + words[1], " ".join(words[2:]))
    if words[0] in {"v.", "V.", "von", "Von"}:
        if words[1].endswith(
            "-v."
        ):  # "v. Wagner-v. Steiger A." -> ('von Wagner-von Steiger', 'A.')
            return (
                "von " + words[1].replace("-v.", "-von") + " " + words[2],
                " ".join(words[3:]),
            )
        return ("von " + words[1], " ".join(words[2:]))
    if len(words) > 1 and words[1] == "-v.":  # "Bucher -v. Trachselwald"
        return (words[0] + "-von " + words[2], " ".join(words[3:]))
    return (words[0], " ".join(words[1:]))


def split_givenname(p):
    if len(p) == 0:
        return ("", [])
    if all(n in GIVEN_NAMES for n in p[0].split()):
        return (p[0], p[1:])
    else:
        return ("", p)


def split_maidenname(n):
    if n.startswith("geb.") or n.startswith("gb."):
        words = n.split()
        if len(words) >= 2:
            if words[1] in {"v.", "V.", "von", "Von"} and len(words) >= 3:
                return ("von " + words[2], " ".join(words[3:]))
            else:
                return (words[1], " ".join(words[2:]))
    return ("", n)


def split_title(p):
    if len(p) > 0 and p[0] in TITLES:
        return (p[0], p[1:])
    else:
        return ("", p)


def split_address(p):
    if len(p) == 0:
        return ("", "", [])
    if is_valid_address(p[0]):
        return (p[0], "", p[1:])
    if is_valid_address(p[-1]):
        return (p[-1], "", p[0:-1])
    last = p[-1].removesuffix(".")
    if m := re.match(r"(.+\d+) ([a-t])", last):
        addr, rest = ("".join(m.groups()), p[:-1])
    elif last and last[-1] in "0123456789":
        addr, rest = (last, p[:-1])
    else:
        return ("", "", p)
    if m := re.match(r"^(.+) (\d+\s?[a-t]?) u\. (\d+\s?[a-t]?)$", addr):
        street, housenum1, housenum2 = m.groups()
        return (f"{street} {housenum1}", f"{street} {housenum2}", rest)
    elif m := re.match(r"^(.+ \d+\s?[a-z]?) u\. (.+)$", addr):
        a1, a2 = m.groups()
        return (a1, a2, rest)
    return (addr, "", rest)


def split_occupation(p):
    if len(p) == 0:
        return ("", p)
    occ = p[0]
    occ = {"Nent.": "Rent."}.get(occ, occ)
    if occ in OCCUPATIONS:
        return (occ, p[1:])
    # Sometimes OCR (or the typesetter) missed a final dot, as in "Schneid"
    if not occ.endswith(".") and occ + "." in OCCUPATIONS:
        return (occ + ".", p[1:])
    return ("", p)


# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )


def create_sheet(workbook, page_id, page_num):
    sheet = workbook.create_sheet(page_num)
    font = openpyxl.styles.Font(name="Calibri", bold=True)
    gray = openpyxl.styles.colors.Color(rgb="00DDDDDD")
    gray_fill = openpyxl.styles.fills.PatternFill(patternType="solid", fgColor=gray)
    cell = sheet.cell(1, 1)
    cell.value = f"https://www.e-rara.ch/bes_1/periodical/pageview/{page_id}"
    cell.font = font
    cell.fill = gray_fill
    sheet.merge_cells("A1:J1")
    for i, col in enumerate(
        [
            "ID",
            "Scan",
            "Name",
            "Vorname",
            "Ledigname",
            "Titel",
            "Beruf",
            "Addresse",
            "Addresse 2",
            "Unklar",
        ]
    ):
        cell = sheet.cell(2, i + 1)
        cell.value = col
        cell.font = font
        cell.fill = gray_fill
    sheet.column_dimensions["A"].width = 3  # ID
    sheet.column_dimensions["B"].width = 35  # Scan
    return sheet


def simplify_pos(pos):
    left, top, right, bottom = 2000, 2977, 0, 0
    for p in pos.split(";"):
        x, y, w, h = [int(x) for x in p.split(",")]
        if h < 0:
            h = 100
        left, right = min(x, left), max(x + w, right)
        top, bottom = min(y, top), max(y + h, bottom)
    left, right = (300, 1050) if left < 600 else (1000, 1750)
    top, bottom = max(top - 5, 0), min(bottom + 5, 2977)
    return (left, top, right - left, bottom - top)


# Fetch the JPEG image for a single page from e-rara.ch.
# If the image is already in cache, the cached content is returned
# without re-downloading it over the internet.
def fetch_jpeg(pageid):
    filepath = os.path.join("cache", "images", f"{pageid}.jpg")
    if not os.path.exists(filepath):
        os.makedirs(os.path.join("cache", "images"), exist_ok=True)
        url = f"https://www.e-rara.ch/download/webcache/2000/{pageid}"
        print(f"fetching {url}")
        with urllib.request.urlopen(url) as u:
            img = u.read()
        # Write to a temp file, followed by (atomic) rename, so we never
        # have partially written files in the final location, even if
        # the process crashes while writing out the file.
        with open(filepath + ".tmp", "wb") as f:
            f.write(img)
        os.rename(filepath + ".tmp", filepath)
    return PIL.Image.open(filepath)


def crop_image(img, pos):
    x, y, w, h = [int(val) for val in pos.split(",")]
    crop = img.reduce(3, (x, y, x + w, y + h))
    out = io.BytesIO()
    crop.save(out, format="PNG")
    return openpyxl.drawing.image.Image(out)


if __name__ == "__main__":
    for vol in list_volumes():
        year = int(os.path.basename(vol)[:4])
        if year >= 1860 and year <= 1860:
            split(vol)
