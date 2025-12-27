# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# GUI tool for manually fixing page column boundaries that have been
# automatically detected with simple computer vision, and which are
# stored in the file data/page_columns.csv.
#
# Usage:
#
#     ./venv/bin/python3 src/cleanup/fix_page_columns.py --year=1863
#
# Keys:
#
#     delete    delete last box (can be pressed multiple times)
#     return    confirm current page, proceed to next page
#     q         quit
#
# When a page is completed, the tool prints a line for each column
# to standard output. Incorporate this into data/page_columns.csv
# using an editor and submit it into the code repository with git.

import argparse
import csv
import os
from pathlib import Path
import urllib.request

import cv2
import numpy as np


# Fetch the JPEG image for a single page from e-rara.ch.
# If the image is already in cache, the cached content is returned
# without re-downloading it over the internet.
def fetch_jpeg(pageid):
    filepath = os.path.join("cache", "images", f"{pageid}.jpg")
    if not os.path.exists(filepath):
        os.makedirs(os.path.join("cache", "images"), exist_ok=True)
        url = f"https://www.e-rara.ch/download/webcache/2000/{pageid}"
        with urllib.request.urlopen(url) as u:
            img = u.read()
        # Write to a temp file, followed by (atomic) rename, so we never
        # have partially written files in the final location, even if
        # the process crashes while writing out the file.
        with open(filepath + ".tmp", "wb") as f:
            f.write(img)
        os.rename(filepath + ".tmp", filepath)
    return filepath


# Returns a map like {"1860-02-01": [29210065, 29210066, ...], ...}
# that tells which volume contains what page IDs.
def read_pages():
    pages = {}
    path = Path(__file__) / ".." / ".." / "pages.csv"
    with open(path.resolve()) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date, pageid = row["Date"], int(row["PageID"])
            pages.setdefault(date, []).append(pageid)
    return pages


class ColumnSelector(object):
    def __init__(self, title, image, rois):
        self.title = title
        self.image = image
        self.pressed = False
        self._rois = rois

    def run(self):
        cv2.namedWindow(self.title)
        cv2.setMouseCallback(self.title, self._on_event)
        done = False
        while True:
            self._redraw()
            key = cv2.waitKey(0)
            if key == 13:  # return
                break
            if key == 127 and len(self._rois) > 0:  # delete
                self._rois = self._rois[:-1]
            if key == ord("q"):
                done = True
                break
        cv2.destroyAllWindows()
        return done, self.rois()

    def rois(self):
        return [self._make_rect(r) for r in self._rois]

    def _on_event(self, event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.pressed = True
            self._rois.append((x, y, 0, 0))
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.pressed:
                self._adjust_roi(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.pressed = False
            self._adjust_roi(x, y)
        self._redraw()

    def _adjust_roi(self, x, y):
        sx, sy = self._rois[-1][0], self._rois[-1][1]
        self._rois[-1] = (sx, sy, x - sx, y - sy)

    def _make_rect(self, r):
        x, y, w, h = r
        x, y = min(x, x + w), min(y, y + h)
        w, h = abs(w), abs(h)
        return (x, y, w, h)

    def _redraw(self):
        canvas = self.image.copy()
        for x, y, w, h in self.rois():
            cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.imshow(self.title, canvas)


# Returns a map page_id -> [(x, y, width, height), ...]
def read_columns():
    columns = {}
    path = Path(__file__) / ".." / ".." / ".." / "data" / "page_columns.csv"
    with open(path.resolve()) as csvfile:
        for row in csv.DictReader(csvfile):
            page_id = int(row["PageID"])
            x, y = int(row["X"]), int(row["Y"])
            width, height = int(row["Width"]), int(row["Height"])
            columns.setdefault(page_id, []).append((x, y, width, height))
    for v in columns.values():
        v.sort()
    return columns


# Parse the string passed as the --years command-line argument.
# For example, "1880-1883,1905" --> {1880, 1881, 1882, 1883, 1905}.
def parse_years(years):
    result = set()
    for s in years.split(","):
        s = s.strip()
        if "-" in s:
            if m := re.match(r"(\d{4})\-(\d{4})", s):
                for year in range(int(m.group(1)), int(m.group(2)) + 1):
                    result.add(year)
            else:
                raise ValueError(f"not in YYYY-YYYY format: {s}")
        else:
            result.add(int(s))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="1863", type=parse_years)
    args = ap.parse_args()
    columns = read_columns()
    for volume, pages in sorted(read_pages().items()):
        year = int(volume[0:4])
        if year not in args.years:
            continue
        for page in pages:
            img_path = fetch_jpeg(page)
            img = cv2.imread(img_path)
            cs = ColumnSelector(f"Page {page}", img, columns.get(page, []))
            done, rois = cs.run()
            for x, y, w, h in rois:
                print(f"{page},{x},{y},{w},{h}")
            if done:
                break
