# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Script for building the final release files. Reads input from `reviewed',
# checks them against various lists of known good names/addresses/professions,
# and builds a CSV file for external distribution.

import csv
import os
import re


class Validator:
    def __init__(self):
        self.family_names = self.read_lines("family_names.txt")
        self.nobility_names = self.read_csv("nobility_names.csv", "Abkürzung")
        self.missing_family_names = set()
        self.re_von = re.compile(r"\b([vV]\.)")  # "Bondeli-v. Allmen"

    def warn(self, message, entry, pos):
        print("%s:%s:%s: %s" % (pos[0], pos[1], entry["Scan"], message))

    def report(self):
        if self.missing_family_names:
            print("Missing family names")
            print("--------------------")
            for name in sorted(self.missing_family_names):
                print(name)

    def validate(self, entry, pos):
        is_company = entry["Titel"] == "[Firma]"
        if is_company:
            return self.validate_company(entry, pos)
        if name := entry["Adelsname"]:
            if name not in self.nobility_names:
                self.warn('unknown nobility name "%s"' % name, entry, pos)
        for p in ("Name", "Ledigname"):
            if is_company and p == "Name":
                continue
            if name := entry[p]:
                name = self.re_von.sub("von", name)
                if name not in self.family_names:
                    self.missing_family_names.add(name)
                    message = '%s "%s" not a known family name' % (p, name)
                    self.warn(message, entry, pos)

    def validate_company(self, entry, pos):
        for p in ("Adelsname", "Ledigname"):
            if entry[p]:
                self.warn("%s should not be set on companies" % p, entry, pos)

    def read_lines(self, filename):
        path = os.path.join(os.path.dirname(__file__), filename)
        lines = set()
        for line in open(path):
            lines.add(line.strip())
        return lines

    def read_csv(self, filename, key):
        path = os.path.join(os.path.dirname(__file__), filename)
        result = {}
        with open(path, mode="r") as stream:
            for row in csv.DictReader(stream):
                assert row[key] not in result, "duplicate entry: %s" % row[0]
                result[row[key]] = row
        return result


if __name__ == "__main__":
    validator = Validator()
    base_dir = os.path.split(os.path.dirname(__file__))[0]
    reviewed_dir = os.path.join(base_dir, "reviewed")
    for filename in sorted(os.listdir(reviewed_dir)):
        path = os.path.join(reviewed_dir, filename)
        line = 1
        with open(path, mode="r") as stream:
            for row in csv.DictReader(stream):
                line += 1
                validator.validate(row, (filename, line))
    validator.report()
