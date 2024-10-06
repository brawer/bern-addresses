# Script for checking the address_mapping.tsv file for the
# 1882 address reform.


from collections import Counter
import csv
import os
import re


class Street(object):
    def __init__(self, name):
        self.name = name
        self.housenumbers = set()


def check(path):
    gwr_streets = read_gwr_streets()
    fp = open(path, "r")
    old_streets = Counter()
    new_streets = Counter()
    missing_streets = {}
    for rec in csv.DictReader(fp, delimiter="\t"):
        id = rec["ID"]
        old_street, new_street = rec["old_streetname"], rec["new_streetname"]
        old_streets[old_street] += 1
        new_streets[new_street] += 1
        old = expand_addresses(id, old_street, rec["old_number"], rec["old_letter"])
        new = expand_addresses(id, new_street, rec["new_number"], rec["new_letter"])
        if new_street not in gwr_streets:
            missing_streets.setdefault(new_street, []).append(id)
    ctr = Counter()
    for name, ids in missing_streets.items():
        ctr[name] += len(ids)
    for street, count in ctr.most_common():
        print(street, count, ",".join(sorted(missing_streets[street])))


def expand_addresses(id, street, numbers, letters):
    if street in ("", "abgebrochen", "Abgebrochen"):
        assert numbers == "", id
        assert letters == "", id
        return [""]
    if numbers == "":
        assert letters == "", id
        return [""]
    if "-" in numbers:
        assert "-" not in letters, id
    addrs = []
    for num in expand_numbers(id, numbers):
        if letters == "":
            addrs.append(f"{street} {num}".strip())
        else:
            for let in expand_letters(id, letters):
                addrs.append(f"{street} {num}{let}".strip())
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


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "address_mapping.tsv")
    check(path)
