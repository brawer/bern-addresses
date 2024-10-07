# Script for checking the address_mapping.tsv file for the
# 1882 address reform.


from collections import Counter
import csv
import io
import os
import re


class Street(object):
    def __init__(self, name):
        self.name = name
        self.housenumbers = set()


def check(path):
    whitelist = read_street_names_whitelist()
    gwr_streets = read_gwr_streets()
    names_2024 = read_street_names_2024()
    abbrevs = read_abbrevs()
    fp = open(path, "r")
    old_streets = Counter()
    new_streets = Counter()
    missing_streets = {}
    missing_buildings = []

    report = io.StringIO()
    writer = csv.writer(report)
    writer.writerow(
        [
            "Strasse vor 1882",
            "Nummer vor 1882",
            "Strasse",
            "Nummer",
            "Scan",
            "ID",
            "Status",
        ]
    )

    for rec in csv.DictReader(fp, delimiter="\t"):
        id = str(int(rec["ID"]))
        assert rec["PDF Page"], rec
        scan_id = 3012646 + int(rec["PDF Page"])
        old_street, new_street = rec["old_streetname"], rec["new_streetname"]
        assert old_street in whitelist, old_street
        old_streets[old_street] += 1
        new_street = rec["new_streetname"]
        new_streets[new_street] += 1
        name_2024 = names_2024.get(new_street, new_street)
        if name_2024 not in gwr_streets and name_2024 not in {
            "",
            "abgebrochen",
            "Abgebrochen",
        }:
            missing_streets.setdefault(name_2024, []).append(id)
        old = expand_addresses(id, old_street, rec["old_number"], rec["old_letter"])
        new = expand_addresses(id, new_street, rec["new_number"], rec["new_letter"])
        for old_street, old_num in old:
            old_street = abbrevs.get(old_street, old_street)
            for new_street, new_num in new:
                new_street = names_2024.get(new_street, new_street)
                if new_street in abbrevs:
                    new_street = abbrevs[new_street]
                gwr_street = gwr_streets.get(new_street)
                if gwr_street == None:
                    status = "Unbekannte Strasse"
                elif new_num not in gwr_street.housenumbers:
                    status = "Unbekannte Hausnummer"
                else:
                    status = "OK"
                writer.writerow(
                    [old_street, old_num, new_street, new_num, scan_id, id, status]
                )
    with open("address_reform_1882.csv", "w") as fp:
        fp.write(report.getvalue())

    ctr = Counter()
    for name, ids in missing_streets.items():
        ctr[name] += len(ids)
    with open("address_reform_1882_streets.txt", "w") as out:
        out.write(
            """Folgende Strassen sind in der Adressreform 1882 als neue Strassennamen
aufgeführt, sind aber nicht im Eidg. Gebäude- und Wohnungsregister (GWR)
erfasst. Die Zahlen sind die Anzahl der Gebäude in der Liste von 1882,
die an der jeweiligen Strasse liegen.

"""
        )
        for street, count in ctr.most_common():
            out.write(f"{count},{street}\n")


def expand_addresses(id, street, numbers, letters):
    street = street.strip()
    numbers = numbers.strip()
    letters = letters.strip()
    if street in ("", "abgebrochen", "Abgebrochen"):
        assert numbers == "", id
        assert letters == "", id
        return [("", "")]
    if numbers == "":
        assert letters == "", id
        return [("", "")]
    if "-" in numbers:
        assert "-" not in letters, id
    addrs = []
    for num in expand_numbers(id, numbers):
        if letters == "":
            addrs.append((street, str(num)))
        else:
            for let in expand_letters(id, letters):
                addrs.append((street, f"{num}{let}".strip()))
    return addrs


def expand_numbers(id, numbers):
    if "-" in numbers:
        low, high = [int(x) for x in numbers.split("-")]
        assert low < high, id
        return [i for i in range(low, high + 1)]
    else:
        return [int(numbers)]


def expand_letters(id, letters):
    if letters == "":
        return []
    if "-" in letters:
        low, high = letters.split("-")
        assert "a" <= low <= "z", id
        assert "a" <= high <= "z", id
        return [chr(x) for x in range(ord(low), ord(high) + 1)]
    elif len(letters) == 1:
        assert "a" <= letters <= "z", id
        return [letters]
    else:
        assert "unespected letters", id


def read_abbrevs():
    abbrevs = {}
    src_path = os.path.dirname(__file__)
    csv_path = os.path.join(src_path, "street_abbrevs.csv")
    with open(csv_path) as fp:
        for rec in csv.DictReader(fp):
            a = rec["Abbreviation"]
            assert a not in abbrevs, a
            abbrevs[a] = rec["Street"]
    return abbrevs


def read_street_names_whitelist():
    streets = set()
    src_path = os.path.dirname(__file__)
    streets_path = os.path.join(src_path, "..", "..", "streets.csv")
    with open(streets_path) as fp:
        for rec in csv.DictReader(fp):
            streets.add(rec["Street"])
    abbrevs_path = os.path.join(src_path, "..", "..", "street_abbrevs.csv")
    with open(abbrevs_path) as fp:
        for rec in csv.DictReader(fp):
            assert rec["Street"] in streets, rec["Street"]
            streets.add(rec["Abbreviation"])
    return streets


def read_gwr_streets():
    src_path = os.path.dirname(__file__)
    project_root = os.path.join(src_path, "..", "..", "..")
    gwr_path = os.path.join(project_root, "data", "gwr_addresses.csv")
    streets = {}
    with open(gwr_path) as fp:
        for rec in csv.DictReader(fp):
            street_name = rec["Strasse"]
            if street_name in streets:
                street = streets[street_name]
            else:
                street = Street(street_name)
                streets[street_name] = street
            street.housenumbers.add(rec["Hausnummer"])
    return streets


def read_street_names_2024():
    updates = {}
    src_path = os.path.dirname(__file__)
    csv_path = os.path.join(src_path, "street_names_2024.csv")
    with open(csv_path) as fp:
        for rec in csv.DictReader(fp):
            name_1882 = rec["Strassenname 1882"]
            name_2024 = rec["Strassenname 2024"]
            assert name_1882 not in updates, name_1882
            updates[name_1882] = name_2024
    return updates


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "address_mapping.tsv")
    check(path)
