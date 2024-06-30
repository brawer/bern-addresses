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
    "Name",
    "Vorname",
    "Ledigname",
    "Adelsname",
    "Titel",
    "Adresse 1",
    "Adresse 2",
    "Beruf 1 (CH-ISCO-19)",
    "Beruf 1 (CH-ISCO-19, männliche Bezeichnung)",
    "Beruf 1 (CH-ISCO-19, weibliche Bezeichnung)",
    "Beruf 2 (CH-ISCO-19)",
    "Beruf 2 (CH-ISCO-19, männliche Bezeichnung)",
    "Beruf 2 (CH-ISCO-19, weibliche Bezeichnung)",
    "Name (Rohtext)",
    "Vorname (Rohtext)",
    "Ledigname (Rohtext)",
    "Adelsname (Rohtext)",
    "Titel (Rohtext)",
    "Adresse 1 (Rohtext)",
    "Adresse 2 (Rohtext)",
    "Beruf 1 (Rohtext)",
    "Beruf 2 (Rohtext)",
    "Bemerkungen",
    "Datum",
    "Seite",
    "Scan",
    "Position (X)",
    "Position (Y)",
    "Position (Breite)",
    "Position (Höhe)",
]


COMPANY_FIELDS = [
    "Name",
    "Adresse 1",
    "Adresse 2",
    "Name (Rohtext)",
    "Adresse 1 (Rohtext)",
    "Adresse 2 (Rohtext)",
    "Tätigkeit 1 (Rohtext)",
    "Tätigkeit 2 (Rohtext)",
    "Bemerkungen",
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
    with zipfile.ZipFile("Berner_Adressbuch.zip", "w") as zf:
        for name, buf in [
            ("Personen.csv", people_buffer),
            ("Firmen.csv", company_buffer),
        ]:
            content = buf.getvalue()
            zf.writestr(name, buf.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
