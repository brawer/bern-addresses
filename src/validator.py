# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Validator detects potential issues with address book entries,
# loading lists of known names, occupations, etc.

import csv
import os
import re


class Validator:
    def __init__(self):
        self.family_names = self.read_lines("family_names.txt")
        self.given_names = self.read_lines("givennames.txt")
        self.nobility_names = self.read_csv("nobility_names.csv", "Abkürzung")
        self.occupations = self.read_csv("occupations.csv", "Occupation")
        self._missing_family_names = set()
        self._re_von = re.compile(r"\b(v\.)")  # "Bondeli-v. Allmen"

    def warn(self, message, entry, pos):
        print("%s:%s:%s: %s" % (pos[0], pos[1], entry["Scan"], message))

    def report(self):
        if self._missing_family_names:
            print("Missing family names")
            print("--------------------")
            for name in sorted(self._missing_family_names):
                print(name)

    def validate(self, entry, pos):
        bad = set()
        if not self.validate_given_name(entry, pos):
            bad.add("Vorname")
        is_company = entry["Titel"] == "[Firma]"
        if is_company:
            bad.update(self.validate_company(entry, pos))
            return bad
        if name := entry["Adelsname"]:
            if name not in self.nobility_names:
                self.warn('unknown nobility name "%s"' % name, entry, pos)
                bad.add("Adelsname")
        for p in ("Name", "Ledigname"):
            if name := entry[p]:
                name = self._re_von.sub("von", name)
                if name not in self.family_names:
                    self._missing_family_names.add(name)
                    message = '%s "%s" not a known family name' % (p, name)
                    self.warn(message, entry, pos)
                    bad.add(p)
        bad.update(self.validate_occupations(entry, pos))
        return bad

    def validate_company(self, entry, pos):
        bad = set()
        for p in ("Adelsname", "Ledigname"):
            if entry[p]:
                self.warn("%s should not be set on companies" % p, entry, pos)
                bad.add(p)
        return bad

    def validate_given_name(self, entry, pos):
        given_names = entry["Vorname"].split()
        ok = all(g in self.given_names for g in given_names)
        if not ok:
            message = 'unknwn given name "%s"' % entry["Vorname"]
            self.warn(message, entry, pos)
        return ok

    def validate_occupations(self, entry, pos):
        bad = set()
        for p in ("Beruf", "Beruf 2"):
            if occ := entry[p]:
                if occ not in self.occupations:
                    self.warn('unknown occupation "%s"' % occ, entry, pos)
                    bad.add(p)
        return bad

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
                assert row[key] not in result, "duplicate entry: %s" % row[key]
                result[row[key]] = row
        return result
