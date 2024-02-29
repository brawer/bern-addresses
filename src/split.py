# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

import csv
import io
import os
import re

GIVENNAMES = {
    line.strip()
    for line in open(os.path.join(os.path.dirname(__file__), "givennames.txt"))
}


def read_occupations():
    occ = {}
    filepath = os.path.join(os.path.dirname(__file__), "occupations.csv")
    with open(filepath) as stream:
        for row in csv.DictReader(stream):
            occ[row["Occupation"]] = row["CH-ISCO-19"]
    return occ


OCCUPATIONS = read_occupations()


def split(vol):
    out = io.StringIO()
    out.write(
        "\t".join(
            [
                "Date",
                "Page",
                "Position",
                "Name",
                "GivenName",
                "MaidenName",
                "Title",
                "Occupation",
                "Address",
                "Address2",
                "Other",
            ]
        )
    )
    out.write("\n")
    page_re = re.compile(r"^# Date: (\d{4}-\d{2}-\d{2}) Page: (\d+)/.*")
    date, page, name = None, None, ""
    for line in open(vol):
        line = line.strip()
        if m := page_re.match(line):
            date, page = m.groups()
            page = f"https://www.e-rara.ch/bes_1/periodical/pageview/{page}"
            out.write("\n")
            continue
        p, pos = line.split("#", 1)
        p = [x.strip() for x in p.split(",")]
        nam, rest = split_familyname(p[0])
        if nam != "-":
            name = nam
        maidenname, rest = split_maidenname(rest)
        p = [rest] + p[1:] if rest else p[1:]
        title, p = split_title(p)
        address, address2, p = split_address(p)
        givenname, p = split_givenname(p)
        occupation, p = split_occupation(p)
        other = ", ".join(p)
        out.write(
            "\t".join(
                [
                    date,
                    page,
                    pos,
                    name,
                    givenname,
                    maidenname,
                    title,
                    occupation,
                    address,
                    address2,
                    other,
                ]
            )
        )
        out.write("\n")
    print(out.getvalue())


def split_familyname(n):
    n = n.replace(" - ", "-")
    words = n.split()
    if words[0] in {"v.", "V.", "von", "Von"}:
        if words[1].endswith(
            "-v."
        ):  # "v. Wagner-v. Steiger A." -> ('von Wagner-von Steiger', 'A.')
            return (
                "von " + words[1].replace("-v.", "-von") + " " + words[2],
                " ".join(words[3:]),
            )
        return ("von " + words[1], " ".join(words[2:]))
    else:
        return (words[0], " ".join(words[1:]))


def split_givenname(p):
    if len(p) == 0:
        return ("", [])
    if all(n in GIVENNAMES for n in p[0].split()):
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
    if len(p) > 0 and p[0] in {
        "älter",
        "jünger",
        "Frau",
        "Dr.",
        "Frauen",
        "Fräul.",
        "Frln.",
        "Frl.",
        "Frau u. Tocht.",
        "Gebr.",
        "Gebrüder",
        "Jgfr.",
        "Jgfrn.",
        "Miß",
        "Frau Oberst",
        "Schwest.",
        "Schwestern",
        "Schwester",
        "Sohn",
        "Söhne",
        "Geschwister",
        "Töcht.",
        "Töchter",
        "Töchtern",
        "Wiw.",
        "Wtw.",
        "Wwe.",
        "Ww.",
        "Vater",
        "Wtw. und Sohn",
    }:
        return (p[0], p[1:])
    else:
        return ("", p)


def split_address(p):
    if len(p) == 0:
        return ("", "", [])
    last = p[-1].removesuffix(".")
    if m := re.match(r"(.+\d+) ([abcdefgh])", last):
        addr, rest = ("".join(m.groups()), p[:-1])
    elif last and last[-1] in "0123456789":
        addr, rest = (last, p[:-1])
    else:
        return ("", "", p)
    if m := re.match(r"^(.+) (\d+\s?[abcdefgh]?) u\. (\d+\s?[abcdefgh]?)$", addr):
        street, housenum1, housenum2 = m.groups()
        return (f"{street} {housenum1}", f"{street} {housenum2}", p)
    elif m := re.match(r"^(.+ \d+\s?[abcdefgh]?) u\. (.+)$", addr):
        a1, a2 = m.groups()
        return (a1, a2, rest)
    return (addr, "", rest)


def split_occupation(p):
    if len(p) > 0 and p[0] in OCCUPATIONS:
        return (p[0], p[1:])
    else:
        return ("", p)


# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )


if __name__ == "__main__":
    for vol in list_volumes():
        if os.path.basename(vol).startswith("1860"):
            split(vol)
