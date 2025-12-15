# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Experimental tool for layout analysis through Computer Vision.
#
# Usage:
#     venv/bin/python3 src/detect_page_rotation.py

import math

import cv2 as cv
import numpy as np

from utils import Page, fetch_jpeg, read_pages

def analyze_page_layout(page: Page, visualize: bool) -> (float, float):
    """
    Detect the rotation of a scanned book page.

    Args:
        page: Book page to be analyzed.

        visualize: Whether to display images with intermediate
            Computer Vision results. Pass True for debugging.

    Returns:
        (page rotation angle in degrees, x offset of vertical divider line).
    """
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
    # We also collect points on the detected divider line, so we can compute
    # its x offset further below.
    sum_length, sum_angle = 0.0, 0.0
    divider_points: list(tuple(float, float, float)) = []  # (x, y, weight)
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
        sum_length += length
        sum_angle += length * angle
        divider_points.append((((x1 + x2) / 2.0), ((y1 + y2) / 2.0), length))
        cv.line(img, (int(x1), int(y1)), (int(x2), int(y2)), (0,0,255), 5)
    if sum_length > 0:
        divider_angle = sum_angle / sum_length
    else:
        # Fallback if we cannot find a line through Computer Vision.
        divider_angle = 0.0

    center = tuple(np.array(img.shape[1::-1]) / 2)
    rotation_matrix = cv.getRotationMatrix2D(center, -divider_angle, 1.0)

    # Calculate the x position of the detected divider line.
    divider_x = img.shape[1] // 2
    if len(divider_points) > 0:
        sum_x, sum_weight = 0.0, 0.0
        for x, y, weight in divider_points:
            rotated_x, _ = transform_point(x, y, rotation_matrix)
            sum_x += rotated_x * weight
            sum_weight += weight
        divider_x = int((sum_x / sum_weight) + 0.5)

    if not visualize:
        return divider_angle, divider_x

    rotated_img = cv.warpAffine(
        img_copy, rotation_matrix, img.shape[1::-1], flags=cv.INTER_LINEAR)
    height, width, _ = img.shape

    # Draw rectangular grids.
    for x in range(0, width, 50):
        w = 4 if x % 250 == 0 else 1
        cv.line(img, (x, 0), (x, height), (255,128,255,64), w)
        cv.line(rotated_img, (x, 0), (x, height), (0,128,255,64), w)
    for y in range(0, height, 50):
        w = 4 if y % 250 == 0 else 1
        cv.line(img, (0, y), (width, y), (255,128,255,64), w)
        cv.line(rotated_img, (0, y), (width, y), (0,128,255,64), w)

    # Draw the detected divider line in the rotated image,
    # including the points which we used to calculatge its x position.
    cv.line(
        rotated_img,
        (divider_x, 0),
        (divider_x, height),
        color=(64, 128, 64, 128),
        thickness=4)
    for x, y, _length in divider_points:
        cv.drawMarker(
            img,
            position=(int(x + 0.5), int(y + 0.5)),
            color=(0, 0, 255, 128),
            markerType=cv.MARKER_STAR,
            markerSize=30,
            thickness=2)
        rotated_x, rotated_y = transform_point(x, y, rotation_matrix)
        cv.drawMarker(
            rotated_img,
            position=(int(rotated_x + 0.5), int(rotated_y + 0.5)),
            color=(64, 128, 64, 128),
            markerType=cv.MARKER_STAR,
            markerSize=30,
            thickness=2)
    cv.imshow("img", img)
    cv.imshow("rotated_img", rotated_img)
    return divider_angle, divider_x

def transform_point(x: float, y: float, matrix) -> (float, float):
    """Transforms a point (x, y) via an affine transformation."""
    return cv.transform(
        np.array([[[x, y]]]),
        matrix)[0][0]


def main():
    for volume, pages in sorted(read_pages().items()):
        year = int(volume[:4])
        if year < 1863:
            continue
        for page in pages:
            if page.id != 29210355: continue
            _angle, _x = analyze_page_layout(page, visualize=True)
            key = cv.waitKey(0)
            if key == ord("q"):
                return


if __name__ == "__main__":
    main()
