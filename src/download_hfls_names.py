# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Download family names from hfls.ch and print those that appear
# as the first words in our scanned address book volumes.
#
# Data fetched with permission from Peter Kessel of hfls.ch.

import os
import re
import requests


def download_family_names():
    url = "http://www.hfls.ch/humo-gen/statistics?menu_tab=stats_surnames&tree_id=1"
    payload = {"freqsurnames": "100000", "maxcols": "1"}
    req = requests.post(url, data=payload)
    text = req.text
    names = set()
    for name in re.findall(r"pers_lastname=(.+?)&amp;", text):
        name = " ".join(name.split())
        if any(c in name for c in ".,()?<>!0123456789\""):
            continue
        if any(w in name for w in (" und ", " oder ")):
            continue
        if name.startswith("a "):
            continue
        names.add(name)
    return names


def read_all_words():
    words = set()
    path = os.path.join(os.path.dirname(__file__),  "..", "proofread")
    path = os.path.normpath(path)
    for filename in os.listdir(path):
        if filename.endswith(".txt"):
            with open(os.path.join(path, filename), "r") as fp:
                for line in fp.readlines():
                    w = line.replace(",", " ").replace(".", " ").split()
                    if len(w) > 2:
                        words.add(w[0])
    return words


if __name__ == "__main__":
    words = read_all_words()
    for name in sorted(download_family_names()):
        if name in words:
            print(name)
