# Script for checking the address_mapping.tsv file for the
# 1882 address reform.


import csv
import os
import re


def check(path):
    fp = open(path, "r")
    hoods = {}
    for rec in csv.DictReader(fp, delimiter="\t"):
        id = rec["ID"]
        hood = rec["neighborhood"]
        hoods.setdefault(rec["old_streetname"], set()).add(hood)
        hoods.setdefault(rec["new_streetname"], set()).add(hood)
        old = expand_addresses(
            id, rec["old_streetname"], rec["old_number"], rec["old_letter"]
        )
        new = expand_addresses(
            id, rec["new_streetname"], rec["new_number"], rec["new_letter"]
        )
    for street, h in hoods.items():
        if len(h) > 1:
            print(street, h)


def expand_addresses(id, street, numbers, letters):
    if street in ("", "abgebrochen", "Abgebrochen"):
        assert numbers == "", id
        assert letters == "", id
        return [""]
    if numbers == "":
        assert letters == "", id
        return [""]
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


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "address_mapping.tsv")
    check(path)
