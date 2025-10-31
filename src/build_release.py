# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Script for building the final release files. Reads input from `reviewed',
# checks them against various lists of known good names/addresses/professions,
# and builds a CSV file for external distribution.

import csv
import io
import os
import zipfile

from validator import Validator


PEOPLE_FIELDS = [
    "ID",
    "Name",
    "Vorname",
    "Geschlecht",
    "Ledigname",
    "Adelsname",
    "Titel",
    "Adresse 1",
    "Adresse 2",
    "Adresse 3",
    "Arbeitsort",
    "Beruf 1 (bereinigt)",
    "Beruf 1 (CH-ISCO-19)",
    "Beruf 2 (bereinigt)",
    "Beruf 2 (CH-ISCO-19)",
    "Beruf 3 (bereinigt)",
    "Beruf 3 (CH-ISCO-19)",
    "Name (Rohtext)",
    "Vorname (Rohtext)",
    "Ledigname (Rohtext)",
    "Adelsname (Rohtext)",
    "Titel (Rohtext)",
    "Adresse 1 (Rohtext)",
    "Adresse 2 (Rohtext)",
    "Adresse 3 (Rohtext)",
    "Adresse 1 (bereinigt, vor Adressreform 1882)",
    "Adresse 2 (bereinigt, vor Adressreform 1882)",
    "Adresse 3 (bereinigt, vor Adressreform 1882)",
    "Beruf 1 (Rohtext)",
    "Beruf 2 (Rohtext)",
    "Beruf 3 (Rohtext)",
    "Datum",
    "Seite",
    "Scan",
    "Position (X)",
    "Position (Y)",
    "Position (Breite)",
    "Position (Höhe)",
]


COMPANY_FIELDS = [
    "ID",
    "Name",
    "Adresse 1",
    "Adresse 2",
    "Adresse 3",
    "Branche 1 (NOGA-Code)",
    "Branche 1 (NOGA-Bezeichnung)",
    "Branche 2 (NOGA-Code)",
    "Branche 2 (NOGA-Bezeichnung)",
    "Branche 3 (NOGA-Code)",
    "Branche 3 (NOGA-Bezeichnung)",
    "Name (Rohtext)",
    "Adresse 1 (Rohtext)",
    "Adresse 2 (Rohtext)",
    "Adresse 3 (Rohtext)",
    "Adresse 1 (bereinigt, vor Adressreform 1882)",
    "Adresse 2 (bereinigt, vor Adressreform 1882)",
    "Adresse 3 (bereinigt, vor Adressreform 1882)",
    "Branche 1 (Rohtext)",
    "Branche 2 (Rohtext)",
    "Branche 3 (Rohtext)",
    "Datum",
    "Seite",
    "Scan",
    "Position (X)",
    "Position (Y)",
    "Position (Breite)",
    "Position (Höhe)",
]


if __name__ == "__main__":
    validator = Validator()
    base_dir = os.path.split(os.path.dirname(__file__))[0]
    reviewed_dir = os.path.join(base_dir, "reviewed")
    people_buffer = io.StringIO()
    people_writer = csv.DictWriter(people_buffer, fieldnames=PEOPLE_FIELDS)
    people_writer.writeheader()
    company_buffer = io.StringIO()
    company_writer = csv.DictWriter(company_buffer, fieldnames=COMPANY_FIELDS)
    company_writer.writeheader()
    for filename in sorted(os.listdir(reviewed_dir)):
        path = os.path.join(reviewed_dir, filename)
        line = 1
        with open(path, mode="r") as stream:
            for row in csv.DictReader(stream):
                line += 1
                validator.validate(row, (filename, line))
                if validator.is_company(row):
                    if norm := validator.normalize_company(row):
                        company_writer.writerow(norm)
                else:
                    if norm := validator.normalize_person(row):
                        people_writer.writerow(norm)

    validator.report()
    unknown_before_1882 = io.StringIO()
    validator.report_unknown_addresses_before_1882(unknown_before_1882)

    with zipfile.ZipFile("Berner_Adressbuch.zip", "w") as zf:
        for name, buf in [
            ("Personen.csv", people_buffer),
            ("Firmen.csv", company_buffer),
            ("Unklare Adressen vor 1882.csv", unknown_before_1882),
        ]:
            content = buf.getvalue()
            zf.writestr(name, buf.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
