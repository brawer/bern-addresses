# SPDX-FileCopyrightText: 2024 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

# Tool for finding column boundaries in images with OpenCV.
# Detected columns are written to this file: data/page_columns.csv
#
# To run: python src/detect_page_columns.py
#
# With --debug, the tool will write a TIFF image with the detected columns.
# With --no-download, the tool will not download uncached pages.

import argparse
import csv
import os
import re

import cv2
import numpy

from split import fetch_jpeg


# Given an OpenCV contour hierarchy, count how many parents
# the i-th contour has in that hierarchy.
def count_parents(hierarchy, i):
    num_parents = 0
    p = hierarchy[0][i][3]
    while p >= 0:
        num_parents += 1
        p = hierarchy[0][p][3]
    return num_parents


def find_columns(page_num, debug_image_path=None):
    image = fetch_jpeg(page_num)
    page = numpy.asarray(image)
    blurred = cv2.bilateralFilter(page, 9, 75, 75)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 40))
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, 1)
    cv2.rectangle(bw, (0, 0), (bw.shape[1] - 1, bw.shape[0] - 1), color=0, thickness=30)
    contours, hierarchy = cv2.findContours(
        bw, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS
    )
    for c, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        white = (count_parents(hierarchy, c) % 2) == 0
        if not white and 650 < w < 900 and h > 100:
            x = x - 5
            y = y - 5
            w = w + 10
            h = h + 10
            yield (x, y, w, h)
            if debug_image_path is not None:
                cv2.rectangle(
                    blurred, (x, y), (x + w, y + h), color=(0, 0, 255), thickness=3
                )
    if debug_image_path is not None:
        cv2.imwrite(debug_image_path, blurred)


def list_all_pages():
    path = os.path.join(os.path.dirname(__file__), "pages.csv")
    pages = []
    with open(path, "r") as fp:
        for row in csv.DictReader(fp):
            pages.append(int(row["PageID"]))
    return pages


def list_cached_pages():
    pages = []
    for filename in os.listdir(os.path.join("cache", "images")):
        if m := re.match(r"(\d+)\.jpg", filename):
            pages.append(int(m.group(1)))
    return pages


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action=argparse.BooleanOptionalAction)
    ap.add_argument("--download", default=True, action=argparse.BooleanOptionalAction)
    args = ap.parse_args()

    pages = list_all_pages() if args.download else list_cached_pages()
    pages.sort()

    path = os.path.join(os.path.dirname(__file__), "..", "data", "page_columns.csv")
    with open(path, "w") as fp:
        writer = csv.writer(fp)
        writer.writerow(["PageID", "X", "Y", "Width", "Height"])
        for page_id in pages:
            print(page_id)
            debug_image_path = f"{page_id}.tif" if args.debug else None
            for x, y, w, h in find_columns(page_id, debug_image_path):
                row = [page_id, x, y, w, h]
                writer.writerow([str(v) for v in row])
