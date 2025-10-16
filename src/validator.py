# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Validator detects potential issues with address book entries,
# loading lists of known names, occupations, etc.

from collections import Counter
import csv
import os
import re

# Recognized columns in input entries for validation/normalization.
# See below for description.
COLUMNS = [
    "ID",
    "Scan",
    "Name",
    "Vorname",
    "Ledigname",
    "Adelsname",
    "Titel",
    "Beruf",
    "Beruf 2",
    "Beruf 3",
    "Adresse",
    "Adresse 2",
    "Adresse 3",
    "Arbeitsort",
    "nicht zuweisbar",
]


# Performs validity checks on an address book entry. Usage:
#
#   val = Validator()
#   bad = val.validate({"Name": "Meier", "Vorname": "Klcra", "Beruf": "xyz"})
#   val.report()
#
# validate() returns a set of keys whose values look suspicious, such as
# {"Vorname", "Beruf"}. If the passed entry passes all checks, the result
# is an empty sety.
#
# report() prints overall validation statistics to standard output, such as
# the number of bad records, or a list of encountered unknown family names.
# Unknown names (and occuptations, streets, etc.) might either be  OCR errors,
# or they are missing from the one of the lists of known names (duh).
#
# is_company() tells if a record is a company, based on the "Title" field.
#
# normalize_person() and normalize_company() expand abbreviations,
# look up statistical codes for occupations, etc. The resulting dictionary
# contains additional attributes. Although this isn't strictly a validation
# task, it uses the same tables, so we decided to put this functionality
# into the Validator class.
#
# The following keys are recognized in the dictionary passed to validate(),
# normalize_person() and normalize_company().
#
# * "Scan": An e-rara.ch page ID, such as "1395972" for the scanned page
#   at https://www.e-rara.ch/bes_1/periodical/pageview/1395972
#
# * "ID": Pixel position on that page as string "x,y,width,height",
#   which uniquely identifies the record on the page.
#
# * "Name": Family or company name, such as
#   "Müller", "von Wurstemberger" or "Ciolina & Comp.".
#
# * "Vorname": Given names, such as "Klara" or "Joh. Friedrich".
#
# * "Ledigname": Unmarried family name, such as "Meier".
#
# * "Adelsname": Nobilty family name, for example "von Burgistein"
#   in a record for "von Graffenried (von Burgistein)".
#
# * "Titel": Title, such as "Frl." or "Prof." The title "[Firma]"
#   indicates a record for a company.
#
# * "Beruf", "Beruf 2", and "Beruf 3": Occupation, such as "Schnd."
#   or "Calligraph".
#
# * "Adresse", "Adresse 2" and "Adresse 3": Possibly abbreviated
#   street address, such as "Metzgg. 96".
#
# * "Arbeitsort": Work place, typically a company name.
class Validator:
    def __init__(self):
        self.columns = set(COLUMNS)
        self.pages = self.read_csv("pages.csv", "PageID")
        self.family_names = self.read_lines("family_names.txt")
        self.given_names = self.read_csv("givennames.txt", "Name")
        self.nobility_names = self.read_csv("nobility_names.csv", "Adelsname (Rohtext)")
        self.titles = self.read_csv("titles.csv", "Title")
        self.occupations = self.read_csv("occupations.csv", "Occupation")
        self.economic_activities = self.read_csv("economic_activities.csv", "Branche")
        self.isco = self.read_csv("HCL_CH_ISCO_19_PROF_1_2_1_level_6.csv", "Code")
        self.noga = self.read_csv("HCL_NOGA_level_5.csv", "Code")
        self.pois = self.read_csv("pois.csv", "PointOfInterest")
        self.street_abbrevs = self.read_csv("street_abbrevs.csv", "Abbreviation")
        self.streets = self.read_csv("streets.csv", "Street")
        self.address_reform_1882 = self.read_address_reform_1882()
        self.unknown_addresses_before_1882 = {}
        for abbr, s in self.street_abbrevs.items():
            street = s["Street"]
            message = 'unknown street "%s" for street_abbrev "%s"' % (street, abbr)
            assert street in self.streets, message
        for occ in self.occupations.values():
            code = occ["CH-ISCO-19"]
            if code == "*":
                continue
            code = code.removesuffix("-EX")
            code = code.removesuffix("-WI")
            assert code in self.isco, "code %s not in CH-ISCO-19 codelist" % code
        self._occupation_counts = Counter()
        self._num_warnings = 0
        self._missing_family_names = set()
        self._missing_given_names = set()
        self._missing_occupations = set()
        self._re_split_addr = re.compile(r"^(.+) (\d+[a-t]?)$")
        self._re_von = re.compile(r"\b(v\.)")  # eg. "v. Bonstetten-de Vigneule"

    def warn(self, message, entry, pos):
        self._num_warnings += 1
        print("%s:%s:%s: %s" % (pos[0], pos[1], entry["Scan"], message))

    def report(self):
        if self._missing_family_names:
            print("Missing family names")
            print("--------------------")
            for name in sorted(self._missing_family_names):
                print(name)
            print()
        if self._missing_given_names:
            print("Missing given names")
            print("-------------------")
            for name in sorted(self._missing_given_names):
                print(name)
            print()
        if self._missing_occupations:
            print("Missing occupations")
            print("-------------------")
            for occ in sorted(self._missing_occupations):
                print(occ)
            print()
        num_ua_before_1882 = len(self.unknown_addresses_before_1882)
        if num_ua_before_1882 > 0:
            print("%d unclear addresses before 1882" % num_ua_before_1882)
        print("%d warnings" % self._num_warnings)

    def report_unknown_addresses_before_1882(self, out):
        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "Unbekannte Adresse",
                "Häufigkeit",
                "Erstes Jahr",
                "Letztes Jahr",
                "Beispiel-Eintrag",
                "Beispiel-Seite",
            ]
        )
        for _, ua in sorted(self.unknown_addresses_before_1882.items()):
            page_id = int(ua.sample_scan["PageID"])
            writer.writerow(
                [
                    ua.address,
                    ua.count,
                    ua.min_year,
                    ua.max_year,
                    ua.sample,
                    f"https://www.e-rara.ch/bes_1/periodical/pageview/{page_id}",
                ]
            )

    def is_company(self, entry):
        return "[Firma]" in entry["Titel"]

    def validate(self, entry, pos):
        assert all(key in self.columns for key in entry.keys()), entry
        bad = set()
        bad.update(self.validate_name(entry, pos))
        given_names_gender, bad_given_name_columns = self.validate_given_names(entry, pos)
        bad.update(bad_given_name_columns)
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
        title_gender, bad_title_columns = self._validate_title(entry, pos)
        bad.update(bad_title_columns)
        bad.update(self.validate_occupations(entry, pos))
        genders = set(g for g in (title_gender, given_names_gender) if g)
        if len(genders) > 1:
            self.warn('inconsistent gender between title and given name', entry, pos)
        return bad

    def validate_name(self, entry, pos):
        bad = set()
        if not entry["Name"].strip():
            self.warn("missing name", entry, pos)
            bad.add("Name")
        return bad

    def validate_addresses(self, entry, pos):
        bad = set()
        if entry["Adresse 2"] and not entry["Adresse"]:
            self.warn("empty address #1", entry, pos)
            bad.add("Adresse")
        if entry["Adresse 3"] and not entry["Adresse 2"]:
            self.warn("empty address #2", entry, pos)
            bad.add("Adresse 2")
        for p in ("Adresse", "Adresse 2", "Adresse 3"):
            if addr := entry[p]:
                if any(a in addr for a in ('Abl.', 'Ablage')):
                    message = '“Ablage” should not be part of address'
                    self.warn(message, entry, pos)
                    bad.add(p)
                    continue
                ok, _normalized = self._normalize_address(addr)
                if not ok:
                    self.warn('unknown address "%s"' % addr, entry, pos)
                    bad.add(p)
                    continue
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
        for p in ("Vorname", "Adelsname", "Ledigname", "Arbeitsort"):
            if entry[p]:
                self.warn("%s should not be set on companies" % p, entry, pos)
                bad.add(p)
        for p in ("Beruf", "Beruf 2", "Beruf 3"):
            if activity := entry[p]:
                if activity not in self.economic_activities:
                    message = 'unknown economic activity "%s"' % activity
                    self.warn(message, entry, pos)
                    bad.add(p)
        return bad

    def validate_given_names(self, entry, pos):
        genders, bad = set(), set()
        for key in ("Vorname",):
            gender, ok = self._validate_given_name(entry, key, pos)
            if gender:
                genders.add(gender)
                if len(genders) > 1:
                    self.warn('inconsistent gender across given names', entry, pos)
                    ok = False
            if not ok:
                bad.add(key)
        single_gender = genders.pop() if len(genders) == 1 else ""
        return single_gender, bad

    def _validate_given_name(self, entry, key, pos):
        given_names = entry[key].split()
        if 'VDM' in given_names or 'V. D. M.' in " ".join(given_names):
            self.warn('VDM is an occupation, not a given name', entry, pos)
            return "", False
        gn = [self.given_names.get(g) for g in given_names]
        ok = all(g != None for g in gn)
        if not ok:
            for n in given_names:
                if n not in self.given_names:
                    self._missing_given_names.add(n)
        if not ok:
            message = 'unknown given name "%s"' % entry[key]
            self.warn(message, entry, pos)
        genders = set(g['Gender'] for g in gn if g != None and g['Gender'])
        if len(genders) > 1:
            message = 'inconsistent gender in %s "%s"' % (key, entry[key])
            self.warn(message, entry, pos)
            ok = False
        gender = genders.pop() if len(genders) == 1 else ""
        return gender, ok

    def validate_occupations(self, entry, pos):
        bad = set()
        for p in ("Beruf", "Beruf 2", "Beruf 3"):
            if occ := entry[p]:
                if occ in self.occupations:
                    self._occupation_counts[occ] += 1
                else:
                    self.warn('unknown occupation "%s"' % occ, entry, pos)
                    bad.add(p)
                    self._missing_occupations.add(occ)
        return bad

    def _validate_title(self, entry, pos):
        title = entry["Titel"]
        if title == "":
            return "", set()
        if t := self.titles.get(title):
            return t["Gender"], set()
        self.warn('unknown title "%s"' % title, entry, pos)
        return "", {"Titel"}

    def normalize_person(self, entry):
        assert not self.is_company(entry)
        scan = self.pages[entry["Scan"]]
        date = scan["Date"]
        _, addr_1 = self._normalize_address(entry["Adresse"])
        _, addr_2 = self._normalize_address(entry["Adresse 2"])
        _, addr_3 = self._normalize_address(entry["Adresse 3"])
        if int(date[:4]) < 1882:
            addr_1_before_1882 = addr_1
            addr_1 = self._modernize_address_1882(addr_1_before_1882, entry)
            addr_2_before_1882 = addr_2
            addr_2 = self._modernize_address_1882(addr_2_before_1882, entry)
            addr_3_before_1882 = addr_3
            addr_3 = self._modernize_address_1882(addr_3_before_1882, entry)
        else:
            addr_1_before_1882 = ""
            addr_2_before_1882 = ""
            addr_3_before_1882 = ""
        occ_1 = self.occupations.get(entry["Beruf"], {}).get("CH-ISCO-19")
        occ_2 = self.occupations.get(entry["Beruf 2"], {}).get("CH-ISCO-19")
        occ_3 = self.occupations.get(entry["Beruf 3"], {}).get("CH-ISCO-19")
        occ_1_male, occ_1_female  = "", ""
        occ_2_male, occ_2_female = "", ""
        occ_3_male, occ_3_female = "", ""
        if occ_1 == "*":
            occ_1 = ""
        if occ_2 == "*":
            occ_2 = ""
        if occ_3 == "*":
            occ_3 = ""
        if occ_1:
            occ_1_key = occ_1.removesuffix("-EX").removesuffix("-WI")
            labels = self.isco[occ_1_key]["Name_de"].split(" | ")
            occ_1_male = labels[0]
            occ_1_female = labels[1] if len(labels) > 1 else labels[0]
        if occ_2:
            occ_2_key = occ_2.removesuffix("-EX").removesuffix("-WI")
            labels = self.isco[occ_2_key]["Name_de"].split(" | ")
            occ_2_male = labels[0]
            occ_2_female = labels[1] if len(labels) > 1 else labels[0]
        if occ_3:
            occ_3_key = occ_3.removesuffix("-EX").removesuffix("-WI")
            labels = self.isco[occ_3_key]["Name_de"].split(" | ")
            occ_3_male = labels[0]
            occ_3_female = labels[1] if len(labels) > 1 else labels[0]
        pos_x, pos_y, pos_w, pos_h = "", "", "", ""
        if pos := entry["ID"]:
            [pos_x, pos_y, pos_w, pos_h] = [str(int(n.strip())) for n in pos.split(",")]
        return {
            "Name": self._normalize_name(entry["Name"]),
            "Vorname": entry["Vorname"],
            "Ledigname": self._normalize_name(entry["Ledigname"]),
            "Adelsname": self._normalize_nobility_name(entry["Adelsname"]),
            "Titel": self._normalize_title(entry["Titel"]),
            "Adresse 1": addr_1,
            "Adresse 2": addr_2,
            "Adresse 3": addr_3,
            "Arbeitsort": entry["Arbeitsort"],
            "Beruf 1 (CH-ISCO-19)": occ_1,
            "Beruf 1 (CH-ISCO-19, männliche Bezeichnung)": occ_1_male,
            "Beruf 1 (CH-ISCO-19, weibliche Bezeichnung)": occ_1_female,
            "Beruf 2 (CH-ISCO-19)": occ_2,
            "Beruf 2 (CH-ISCO-19, männliche Bezeichnung)": occ_2_male,
            "Beruf 2 (CH-ISCO-19, weibliche Bezeichnung)": occ_2_female,
            "Beruf 3 (CH-ISCO-19)": occ_3,
            "Beruf 3 (CH-ISCO-19, männliche Bezeichnung)": occ_3_male,
            "Beruf 3 (CH-ISCO-19, weibliche Bezeichnung)": occ_3_female,
            "Name (Rohtext)": entry["Name"],
            "Vorname (Rohtext)": entry["Vorname"],
            "Ledigname (Rohtext)": entry["Ledigname"],
            "Adelsname (Rohtext)": entry["Adelsname"],
            "Titel (Rohtext)": entry["Titel"],
            "Adresse 1 (Rohtext)": entry["Adresse"],
            "Adresse 2 (Rohtext)": entry["Adresse 2"],
            "Adresse 3 (Rohtext)": entry["Adresse 3"],
            "Adresse 1 (bereinigt, vor Adressreform 1882)": addr_1_before_1882,
            "Adresse 2 (bereinigt, vor Adressreform 1882)": addr_2_before_1882,
            "Adresse 3 (bereinigt, vor Adressreform 1882)": addr_3_before_1882,
            "Beruf 1 (Rohtext)": entry["Beruf"],
            "Beruf 2 (Rohtext)": entry["Beruf 2"],
            "Beruf 3 (Rohtext)": entry["Beruf 3"],
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
        pos_x, pos_y, pos_w, pos_h = "", "", "", ""
        if pos := entry["ID"]:
            [pos_x, pos_y, pos_w, pos_h] = [str(int(n.strip())) for n in pos.split(",")]
        scan = self.pages[entry["Scan"]]
        date = scan["Date"]

        _, addr_1 = self._normalize_address(entry["Adresse"])
        _, addr_2 = self._normalize_address(entry["Adresse 2"])
        _, addr_3 = self._normalize_address(entry["Adresse 3"])
        if int(date[:4]) < 1882:
            addr_1_before_1882 = addr_1
            addr_1 = self._modernize_address_1882(addr_1_before_1882, entry)
            addr_2_before_1882 = addr_2
            addr_2 = self._modernize_address_1882(addr_2_before_1882, entry)
            addr_3_before_1882 = addr_3
            addr_3 = self._modernize_address_1882(addr_3_before_1882, entry)
        else:
            addr_1_before_1882 = ""
            addr_2_before_1882 = ""
            addr_3_before_1882 = ""

        noga_code_1, noga_label_1  = "", ""
        noga_code_2, noga_label_2 = "", ""
        noga_code_3, noga_label_3 = "", ""
        if activity_1 := self.economic_activities.get(entry["Beruf"]):
            noga_code_1 = activity_1["NOGA-Code"]
            noga_label_1 = self.noga[noga_code_1]["Name_de"]
        activity_2 = self.economic_activities.get(entry["Beruf 2"])
        if activity_2 := self.economic_activities.get(entry["Beruf 2"]):
            noga_code_2 = activity_2["NOGA-Code"]
            noga_label_2 = self.noga[noga_code_2]["Name_de"]
        activity_3 = self.economic_activities.get(entry["Beruf 3"])
        if activity_3 := self.economic_activities.get(entry["Beruf 3"]):
            noga_code_3 = activity_3["NOGA-Code"]
            noga_label_3 = self.noga[noga_code_2]["Name_de"]
        return {
            "Name": self._normalize_company_name(entry["Name"]),
            "Adresse 1": addr_1,
            "Adresse 2": addr_2,
            "Adresse 3": addr_3,
            "Branche 1 (NOGA-Code)": noga_code_1,
            "Branche 1 (NOGA-Bezeichnung)": noga_label_1,
            "Branche 2 (NOGA-Code)": noga_code_2,
            "Branche 2 (NOGA-Bezeichnung)": noga_label_2,
            "Branche 3 (NOGA-Code)": noga_code_3,
            "Branche 3 (NOGA-Bezeichnung)": noga_label_3,
            "Name (Rohtext)": entry["Name"],
            "Adresse 1 (Rohtext)": entry["Adresse"],
            "Adresse 2 (Rohtext)": entry["Adresse 2"],
            "Adresse 3 (Rohtext)": entry["Adresse 3"],
            "Adresse 1 (bereinigt, vor Adressreform 1882)": addr_1_before_1882,
            "Adresse 2 (bereinigt, vor Adressreform 1882)": addr_2_before_1882,
            "Adresse 3 (bereinigt, vor Adressreform 1882)": addr_3_before_1882,
            "Branche 1 (Rohtext)": entry["Beruf"],
            "Branche 2 (Rohtext)": entry["Beruf 2"],
            "Branche 3 (Rohtext)": entry["Beruf 3"],
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
        # so we need to check for POIs before anything else.
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

    def _modernize_address_1882(self, addr, entry):
        if addr == "":
            return ""
        if a := self.address_reform_1882.get(addr):
            return a
        if a := self.address_reform_1882.get(addr.replace("ß", "ss")):
            return a

        scan = self.pages[entry["Scan"]]
        year = int(scan["Date"][:4])
        if ua := self.unknown_addresses_before_1882.get(addr):
            ua.count += 1
            ua.min_year = min(ua.min_year, year)
            ua.max_year = max(ua.max_year, year)
            return ""

        # Build a sample, so humans can follow up on unknown addresses.
        name = self._normalize_name(entry["Name"])
        givenname = entry["Vorname"]
        sample = f"{name} {givenname}".strip()
        ua = UnknownAddress()
        ua.address = addr
        ua.count = 1
        ua.sample = sample
        ua.sample_scan = scan
        ua.min_year = year
        ua.max_year = year
        self.unknown_addresses_before_1882[addr] = ua

        return ""

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

    def read_address_reform_1882(self):
        data_path = os.path.join(os.path.dirname(__file__), "..", "data")
        path = os.path.join(data_path, "address_reform_1882.csv")
        result = {}
        # Keys as printed in "Die Häuser-Nummerirung in Bern 1882"
        # and thus as "Strasse vor 1882" in data/address_reform_1882.csv;
        # values as in src/streets.csv.
        old_street_subst = {
            "Aarzieledrittel": "Aarziele",
            "Arziele-Drittel": "Aarziele",
            "Aarziele-Drittel": "Aarziele",
            "Altenberg-Drittel": "Altenberg",
            "Brunnadern-Drittel": "Brunnadern",
            "Holligen-Drittel": "Holligen",
            "Länggass-Drittel": "Länggasse",
            "Lorraine-Drittel": "Lorraine",
            "Lorraine-Strasse": "Lorrainestrasse",
            "Schosshalden-Drittel": "Schosshalde",
            "Zwiebelngässchen": "Zwiebelngässlein",
        }
        with open(path, "r") as stream:
            for r in csv.DictReader(stream):
                old_street = r["Strasse vor 1882"]
                old_street = old_street_subst.get(old_street, old_street)
                old_num = r["Nummer vor 1882"]
                new_street = r["Strasse"]
                new_num = r["Nummer"]
                old_addr = f"{old_street} {old_num}".strip()
                new_addr = f"{new_street} {new_num}".strip()
                if old_addr and new_addr:
                    result[old_addr] = new_addr
        return result


class UnknownAddress(object):
    def __init__(self):
        self.address = None
        self.count = 0
        self.sample = ""
        self.sample_scan = None
