# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Read a CSV file that is formatted in the style of Microsoft Excel,
# writing its content again as a CSV to standard output, UNIX/Python style.
#
# Usage: python3 src/cleanup/read_excel_csv.py path/to/data.csv

import argparse
import csv
import sys

def process(path):
    out = csv.writer(sys.stdout)
    with open(path, "r", encoding="utf-8") as fp:
        for row in csv.reader(fp, delimiter=";"):
            row = [c.removeprefix("\uFEFF") for c in row]
            out.writerow(row)

        
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input.csv")
    args = ap.parse_args()
    process(args.__getattribute__("input.csv"))
