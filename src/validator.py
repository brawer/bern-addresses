# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Validator detects potential issues with address book entries,
# loading lists of known names, occupations, etc.

from collections import Counter
import csv
import os
import re


class Validator:
    def __init__(self):
        self.pages = self.read_csv("pages.csv", "PageID")
        self.family_names = self.read_lines("family_names.txt")
        self.given_names = self.read_lines("givennames.txt")
        self.nobility_names = self.read_csv("nobility_names.csv", "Adelsname (Rohtext)")
        self.titles = self.read_csv("titles.csv", "Title")
        self.occupations = self.read_csv("occupations.csv", "Occupation")
        self.economic_activities = self.read_csv("economic_activities.csv", "Branche")
        self.isco = self.read_csv("HCL_CH_ISCO_19_PROF_1_2_1_level_6.csv", "Code")
        self.noga = self.read_csv("HCL_NOGA_level_5.csv", "Code")
        self.pois = self.read_csv("pois.csv", "PointOfInterest")
        self.street_abbrevs = self.read_csv("street_abbrevs.csv", "Abbreviation")
        self.streets = self.read_csv("streets.csv", "Street")
        for abbr, s in self.street_abbrevs.items():
            street = s["Street"]
            message = 'unknown street "%s" for street_abbrev "%s"' % (street, abbr)
            assert street in self.streets, message
        for occ in self.occupations.values():
            code = occ["CH-ISCO-19"]
            if code == "*":
                continue
            code = code.removesuffix("-EX")
            assert code in self.isco, "code %s not in CH-ISCO-19 codelist" % code
        self._occupation_counts = Counter()
        self._num_warnings = 0
        self._missing_family_names = set()
        self._re_split_addr = re.compile(r"^(.+) (\d+[a-t]?)$")
        self._re_von = re.compile(r"\b(v\.)")  # eg. "v. Bonstetten-de Vigneule"

    def warn(self, message, entry, pos):
        self._num_warnings += 1
        print("%s:%s:%s: %s" % (pos[0], pos[1], entry["Scan"], message))

    def report(self):
        for occ in self.occupations:
            if occ not in self._occupation_counts:
                print('src/occupatons.csv: unused entry "%s"' % occ)
        if self._missing_family_names:
            print("Missing family names")
            print("--------------------")
            for name in sorted(self._missing_family_names):
                print(name)
        print()
        print("%d warnings" % self._num_warnings)

    def is_company(self, entry):
        return "[Firma]" in entry["Titel"]

    def validate(self, entry, pos):
        bad = set()
        if not self.validate_given_name(entry, pos):
            bad.add("Vorname")
        bad.update(self.validate_addresses(entry, pos))
        if self.is_company(entry):
            bad.update(self.validate_company(entry, pos))
            return bad
        if name := entry["Adelsname"]:
            if name not in self.nobility_names:
                self.warn('unknown nobility name "%s"' % name, entry, pos)
                bad.add("Adelsname")
        for p in ("Name", "Ledigname"):
            if name := entry[p]:
                name = self._normalize_name(name)
                if name not in self.family_names:
                    self._missing_family_names.add(name)
                    message = '%s "%s" not a known family name' % (p, name)
                    self.warn(message, entry, pos)
                    bad.add(p)
        bad.update(self.validate_title(entry, pos))
        bad.update(self.validate_occupations(entry, pos))
        return bad

    def validate_addresses(self, entry, pos):
        bad = set()
        if entry["Adresse 2"] and not entry["Adresse"]:
            self.warn("empty address #1", entry, pos)
            bad.add("Adresse")
        for p in ("Adresse", "Adresse 2"):
            if addr := entry[p]:
                ok, _normalized = self._normalize_address(addr)
                if not ok:
                    self.warn('unknown address "%s"' % addr, entry, pos)
                    bad.add(p)
        return bad

    def validate_company(self, entry, pos):
        bad = set()
        if entry["Titel"] != "[Firma]":
            self.warn(
                'title "%s" should just be "[Firma]", move rest to name'
                % entry["Titel"],
                entry,
                pos,
            )
            bad.add("Titel")
        for p in ("Adelsname", "Ledigname"):
            if entry[p]:
                self.warn("%s should not be set on companies" % p, entry, pos)
                bad.add(p)
        for p in ("Beruf", "Beruf 2"):
            if activity := entry[p]:
                if activity not in self.economic_activities:
                    message = 'unknown economic activity "%s"' % activity
                    self.warn(message, entry, pos)
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
                if occ in self.occupations:
                    self._occupation_counts[occ] += 1
                else:
                    self.warn('unknown occupation "%s"' % occ, entry, pos)
                    bad.add(p)
        return bad

    def validate_title(self, entry, pos):
        title = entry["Titel"]
        if title == "" or title in self.titles:
            return set()
        self.warn('unknown title "%s"' % title, entry, pos)
        return {"Titel"}

    def normalize_person(self, entry):
        assert not self.is_company(entry)
        _, addr_1 = self._normalize_address(entry["Adresse"])
        _, addr_2 = self._normalize_address(entry["Adresse 2"])
        occ_1 = self.occupations.get(entry["Beruf"], {}).get("CH-ISCO-19")
        occ_2 = self.occupations.get(entry["Beruf 2"], {}).get("CH-ISCO-19")
        occ_1_male, occ_1_female, occ_2_male, occ_2_female = "", "", "", ""
        if occ_1 == "*":
            occ_1 = ""
        if occ_2 == "*":
            occ_2 = ""
        if occ_1:
            labels = self.isco[occ_1.removesuffix("-EX")]["Name_de"].split(" | ")
            occ_1_male = labels[0]
            occ_1_female = labels[1] if len(labels) > 1 else labels[0]
        if occ_2:
            labels = self.isco[occ_2.removesuffix("-EX")]["Name_de"].split(" | ")
            occ_2_male = labels[0]
            occ_2_female = labels[1] if len(labels) > 1 else labels[0]
        pos_x, pos_y, pos_w, pos_h = "", "", "", ""
        if pos := entry["ID"]:
            [pos_x, pos_y, pos_w, pos_h] = [str(int(n.strip())) for n in pos.split(",")]
        scan = self.pages[entry["Scan"]]
        return {
            "Name": self._normalize_name(entry["Name"]),
            "Vorname": entry["Vorname"],
            "Ledigname": self._normalize_name(entry["Ledigname"]),
            "Adelsname": self._normalize_nobility_name(entry["Adelsname"]),
            "Titel": self._normalize_title(entry["Titel"]),
            "Adresse 1": addr_1,
            "Adresse 2": addr_2,
            "Beruf 1 (CH-ISCO-19)": occ_1,
            "Beruf 1 (CH-ISCO-19, männliche Bezeichnung)": occ_1_male,
            "Beruf 1 (CH-ISCO-19, weibliche Bezeichnung)": occ_1_female,
            "Beruf 2 (CH-ISCO-19)": occ_2,
            "Beruf 2 (CH-ISCO-19, männliche Bezeichnung)": occ_2_male,
            "Beruf 2 (CH-ISCO-19, weibliche Bezeichnung)": occ_2_female,
            "Name (Rohtext)": entry["Name"],
            "Vorname (Rohtext)": entry["Vorname"],
            "Ledigname (Rohtext)": entry["Ledigname"],
            "Adelsname (Rohtext)": entry["Adelsname"],
            "Titel (Rohtext)": entry["Titel"],
            "Adresse 1 (Rohtext)": entry["Adresse"],
            "Adresse 2 (Rohtext)": entry["Adresse 2"],
            "Beruf 1 (Rohtext)": entry["Beruf"],
            "Beruf 2 (Rohtext)": entry["Beruf 2"],
            "Bemerkungen": entry["Bemerkungen"],
            "Datum": scan["Date"],
            "Seite": scan["PageLabel"],
            "Scan": entry["Scan"],
            "Position (X)": pos_x,
            "Position (Y)": pos_y,
            "Position (Breite)": pos_w,
            "Position (Höhe)": pos_h,
        }

    def normalize_company(self, entry):
        assert self.is_company(entry)
        _, addr_1 = self._normalize_address(entry["Adresse"])
        _, addr_2 = self._normalize_address(entry["Adresse 2"])
        pos_x, pos_y, pos_w, pos_h = "", "", "", ""
        if pos := entry["ID"]:
            [pos_x, pos_y, pos_w, pos_h] = [str(int(n.strip())) for n in pos.split(",")]
        scan = self.pages[entry["Scan"]]
        noga_code_1, noga_label_1, noga_code_2, noga_label_2 = "", "", "", ""
        if activity_1 := self.economic_activities.get(entry["Beruf"]):
            noga_code_1 = activity_1["NOGA-Code"]
            noga_label_1 = self.noga[noga_code_1]["Name_de"]
        activity_2 = self.economic_activities.get(entry["Beruf 2"])
        if activity_2 := self.economic_activities.get(entry["Beruf 2"]):
            noga_code_2 = activity_2["NOGA-Code"]
            noga_label_2 = self.noga[noga_code_2]["Name_de"]
        return {
            "Name": self._normalize_company_name(entry["Name"]),
            "Adresse 1": addr_1,
            "Adresse 2": addr_2,
            "Branche 1 (NOGA-Code)": noga_code_1,
            "Branche 1 (NOGA-Bezeichnung)": noga_label_1,
            "Branche 2 (NOGA-Code)": noga_code_2,
            "Branche 2 (NOGA-Bezeichnung)": noga_label_2,
            "Name (Rohtext)": entry["Name"],
            "Adresse 1 (Rohtext)": entry["Adresse"],
            "Adresse 2 (Rohtext)": entry["Adresse 2"],
            "Branche 1 (Rohtext)": entry["Beruf"],
            "Branche 2 (Rohtext)": entry["Beruf 2"],
            "Bemerkungen": entry["Bemerkungen"],
            "Datum": scan["Date"],
            "Seite": scan["PageLabel"],
            "Scan": entry["Scan"],
            "Position (X)": pos_x,
            "Position (Y)": pos_y,
            "Position (Breite)": pos_w,
            "Position (Höhe)": pos_h,
        }

    def _normalize_name(self, name):
        return self._re_von.sub("von", name)

    def _normalize_company_name(self, name):
        abbrevs = {
            "v.": "von",
            "u.": "und",
            "Cie.": "Compagnie",
            "Comp.": "Compagnie",
            "Gebr.": "Gebrüder",
            "Gebrd.": "Gebrüder",
            "Schwst.": "Schwestern",
            "Töcht.": "Töchter",
        }
        words = [abbrevs.get(w, w) for w in name.split()]
        return " ".join(words)

    def _normalize_nobility_name(self, name):
        if entry := self.nobility_names.get(name):
            return entry["Adelsname (bereinigt)"]
        else:
            return name

    def _normalize_title(self, title):
        if t := self.titles.get(title):
            return t["Normalized"]
        else:
            return title

    def _normalize_address(self, addr):
        # Some POIs such as "Kaserne 1" look like street + number,
        # so we need to check for POIS before anything else.
        if poi := self.pois.get(addr):
            return True, poi["Normalized"]
        if m := self._re_split_addr.match(addr):
            street, num = m.groups()
            if abbrev := self.street_abbrevs.get(street):
                street = abbrev["Street"]
            normalized = "%s %s" % (street, num)
            ok = street in self.streets
            return (ok, normalized)
        if addr in self.streets:
            return True, addr
        if abbrev := self.street_abbrevs.get(addr):
            return True, abbrev["Street"]
        return False, ""

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
