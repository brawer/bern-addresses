# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Experimental tool for detecting page rotation through Computer Vision.
#
# Usage:
#     venv/bin/python3 src/detect_page_rotation.py

import math

import cv2 as cv
import numpy as np

from utils import fetch_jpeg, read_pages

def detect_page_rotation(page):
    print(page)
    img = cv.imread(fetch_jpeg(page.id))
    img_copy = img.copy()

    dx, dy = 600, 250
    blurred = cv.bilateralFilter(img, 9, 75, 75)
    height, width, _ = blurred.shape
    blurred = blurred[dy:height-dy, dx:width-dx]
    gray = cv.cvtColor(blurred, cv.COLOR_BGR2GRAY)
    lsd = cv.createLineSegmentDetector(cv.LSD_REFINE_ADV)
    lines, _width, _prec, _nfa = lsd.detect(gray)

    # For each (reasonably long and reasonably vertical) detected line segment,
    # compute its angle, and aggregate these angles in proportion to the
    # segment length. Longer segments have a larger weight in the total angle.
    total_length, total_angle = 0.0, 0.0
    for ((x1, y1, x2, y2),) in lines:
        x1, y1, x2, y2 = x1 + dx, y1 + dy, x2 + dx, y2 + dy
        width, height = x2 - x1, y2 - y1
        length = math.sqrt(width * width + height * height)
        if length < 300:
            continue
        angle = math.degrees(math.sin(width / length))
        if y1 > y2:
            angle = -angle
        if abs(angle) >= 10:
            continue
        total_length += length
        total_angle += length * angle
        cv.line(img, (int(x1), int(y1)), (int(x2), int(y2)), (0,0,255), 5)
    if total_length > 0:
        angle = total_angle / total_length
    else:
        angle = 0.0
    print(angle)

    center = tuple(np.array(img.shape[1::-1]) / 2)
    rotation_matrix = cv.getRotationMatrix2D(center, -angle, 1.0)
    rotated_img = cv.warpAffine(
        img_copy, rotation_matrix, img.shape[1::-1], flags=cv.INTER_LINEAR)
    height, width, _ = img.shape
    for x in range(0, width, 50):
        w = 4 if x % 250 == 0 else 1
        cv.line(img, (x, 0), (x, height), (255,128,255), w)
        cv.line(rotated_img, (x, 0), (x, height), (0,128,255), w)
    for y in range(0, height, 50):
        w = 4 if y % 250 == 0 else 1
        cv.line(img, (0, y), (width, y), (255,128,255), w)
        cv.line(rotated_img, (0, y), (width, y), (0,128,255), w)
    cv.imshow("img", img)
    cv.imshow("rotated_img", rotated_img)
    key = cv.waitKey(0)
    return key != ord("q")


def main():
    for volume, pages in sorted(read_pages().items()):
        year = int(volume[:4])
        if year < 1860:
            continue
        for page in pages:
            if not detect_page_rotation(page):
                return


if __name__ == "__main__":
    main()
