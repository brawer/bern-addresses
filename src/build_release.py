# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Script for building the final release files. Reads input from `reviewed',
# checks them against various lists of known good names/addresses/professions,
# and builds a CSV file for external distribution.

import csv
import os

from validator import Validator


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
