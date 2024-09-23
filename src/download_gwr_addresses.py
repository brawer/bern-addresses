# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Download data files of the Swiss Federal Buildings Registry
# (Gebäude- und Wohnungsregister, GWR) and extract addresses
# relevant for our project.
#
# This script generates the data file in data/gwr_addresses.csv.
# To refresh that data file, which is probably never needed,
# re-run the script like this:
#
# $ git checkout git@github.com:brawer/bern-addresses.git
# $ cd bern-addresses
# $ python3 -m venv venv
# $ venv/bin/pip3 install -r requirements.txt
# $ venv/bin/python3 src/download_gwr_addresses.py
# $ git diff data/gwr_addresses.csv

import csv
import io
import os.path
import re
import tempfile
import zipfile
from collections import namedtuple
from urllib.request import urlopen

import pyproj

GWR_BERN_URL = "https://public.madd.bfs.admin.ch/be.zip"


def download(url, zip_path):
    with open(zip_path, "wb") as fp:
        with urlopen(url) as stream:
            fp.write(stream.read())


def extract(zip_path, out_path):
    # Swiss LV95 (https://epsg.io/2056) -> WGS84 lat/lon (https://epsg.io/4326)
    transformer = pyproj.Transformer.from_crs(2056, 4326)
    with zipfile.ZipFile(zip_path) as zip_file:
        buildings = {}
        Building = namedtuple("Building", "egid construction demolition")
        for b in read_csv(zip_file, "gebaeude_batiment_edificio.csv"):
            egid = int(b["EGID"])
            construction = b["GBAUJ"]
            if construction and b["GBAUM"]:
                construction = construction + "-%02d" % int(b["GBAUM"])
            demolition = b["GABBJ"]  # demolition month is not part of data
            buildings[egid] = Building(egid, construction, demolition)
        with open(out_path, "w") as out:
            writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(
                [
                    "Strasse",
                    "Hausnummer",
                    "PLZ",
                    "Ort",
                    "EGID",
                    "Breitengrad",
                    "Längengrad",
                    "Bau",
                    "Abbruch",
                ]
            )
            rows = []
            for e in read_csv(zip_file, "eingang_entree_entrata.csv"):
                if e["DPLZNAME"] != "Bern":
                    continue
                egid = int(e["EGID"])
                street, housenumber = e["STRNAME"], e["DEINR"]
                if street == "":
                    continue
                postcode, city = e["DPLZ4"], e["DPLZNAME"]
                if e["DKODE"] and e["DKODN"]:
                    east, north = float(e["DKODE"]), float(e["DKODN"])
                    lat, lon = transformer.transform(east, north)
                else:
                    lat, lon = None, None
                if building := buildings.get(egid):
                    construction = building.construction
                    demolition = building.demolition
                else:
                    construction, demolition = "", ""
                row = [
                    street,
                    housenumber,
                    postcode,
                    city,
                    str(egid),
                    "%.7f" % lat if lat is not None else "",
                    "%.7f" % lon if lon is not None else "",
                    construction,
                    demolition,
                ]
                rows.append(row)
            for row in sorted(rows, key=row_sort_key):
                writer.writerow(row)


def row_sort_key(row):
    street, num = row[0], row[1]
    if m := re.match(r"(^\d+)(.*)$", num):
        housenumber, suffix = int(m.group(1)), m.group(2)
    elif re.match(r"\d+", num):
        housenumber, suffix = int(num), ""
    else:
        housenumber, suffix = 0, num
    return (street, housenumber, suffix, row[2:])


def read_csv(zip_file, filename):
    with zip_file.open(filename, mode="r") as f:
        stream = io.TextIOWrapper(f, encoding="utf-8")
        reader = csv.reader(stream, delimiter="\t")
        header = next(reader)
        for row in reader:
            yield dict(zip(header, row))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "be.zip")
        out_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "gwr_addresses.csv"
        )
        download(GWR_BERN_URL, zip_path)
        extract(zip_path, out_path)
