# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Experimental tool for layout analysis through Computer Vision.
#
# Usage:
#     venv/bin/python3 src/layout.py --pages=29210355
#     venv/bin/python3 src/layout.py --years=1863-1864,1921

from argparse import ArgumentParser
from dataclasses import dataclass
import math

import cv2 as cv
import numpy as np

from utils import Page, fetch_jpeg, parse_pages, parse_years, read_pages


@dataclass
class LineSegment:
    x1: float
    y1: float
    x2: float
    y2: float

    def length(self) -> float:
        width = self.x2 - self.x1
        height = self.y2 - self.y1
        return math.sqrt(width * width + height * height)

    def angle(self) -> float:
        width = self.x2 - self.x1
        length = self.length()
        if length == 0.0:
            return 0.0
        angle = math.degrees(math.sin(width / length))
        if self.y1 > self.y2:
            angle = -angle
        return angle


class LayoutAnalysis(object):
    def __init__(self, page: Page):
        self.page = page
        self.raw_image = cv.imread(fetch_jpeg(page.id))
        self.divider_segments = self._detect_divider_segments()
        self._detect_rotation()
        self._detect_divider_x()

    def _detect_divider_segments(self) -> list[LineSegment]:
        segments: list[LineSegment] = []
        img = self.raw_image
        dx, dy = 600, 250
        blurred = cv.bilateralFilter(img, 9, 75, 75)
        height, width, _ = blurred.shape
        blurred = blurred[dy : height - dy, dx : width - dx]
        gray = cv.cvtColor(blurred, cv.COLOR_BGR2GRAY)
        lsd = cv.createLineSegmentDetector(cv.LSD_REFINE_ADV)
        lines, _width, _prec, _nfa = lsd.detect(gray)
        for ((x1, y1, x2, y2),) in lines:
            segment = LineSegment(x1 + dx, y1 + dy, x2 + dx, y2 + dy)
            length = segment.length()
            if length < 300:
                continue
            angle = segment.angle()
            if abs(angle) >= 5:
                continue
            segments.append(segment)
        segments.sort(key=lambda s: (s.y1 + s.y2) / 2.0)
        return segments

    def _detect_rotation(self) -> None:
        self.rotation_angle = 0.0
        if len(self.divider_segments) > 0:
            sum_angle, sum_length = 0.0, 0.0
            for s in self.divider_segments:
                length = s.length()
                sum_angle += s.angle() * length
                sum_length += length
            self.rotation_angle = -(sum_angle / sum_length)
        center = tuple(np.array(self.raw_image.shape[1::-1]) / 2)
        self.rotation_matrix = cv.getRotationMatrix2D(center, self.rotation_angle, 1.0)

    def _detect_divider_x(self) -> None:
        if len(self.divider_segments) == 0:
            self.divider_x = self.raw_image.shape[1] // 2
            return
        sum_x, sum_weight = 0.0, 0.0
        for s in self.divider_segments:
            weight = s.length()
            rotated_x1, _ = self._transform_point(s.x1, s.y1, self.rotation_matrix)
            rotated_x2, _ = self._transform_point(s.x2, s.y2, self.rotation_matrix)
            sum_x += rotated_x1 * weight + rotated_x2 * weight
            sum_weight += weight * 2
        self.divider_x = int((sum_x / sum_weight) + 0.5)

    def debug_image(self) -> np.ndarray:
        image = self.raw_image.copy()
        height, width, num_channels = image.shape
        self._draw_grid(image, color=(255, 128, 255))
        self._draw_divider_segments(
            image, segments=self.divider_segments, color=(128, 128, 255)
        )

        rotated_image = cv.warpAffine(
            self.raw_image,
            self.rotation_matrix,
            self.raw_image.shape[1::-1],
            flags=cv.INTER_LINEAR,
        )
        self._draw_grid(rotated_image, color=(0, 128, 255))
        cv.line(
            rotated_image,
            (self.divider_x, 0),
            (self.divider_x, height),
            color=(64, 128, 64),
            thickness=3,
        )

        result = np.zeros((height, width * 2, num_channels), dtype=np.uint8)
        result[0:height, 0:width] = image
        result[0:height, width : width * 2] = rotated_image
        return result

    @staticmethod
    def _draw_grid(image, color):
        height, width, _ = image.shape
        for x in range(0, width, 50):
            line_width = 3 if x % 250 == 0 else 1
            cv.line(image, (x, 0), (x, height), color, line_width)
        for y in range(0, height, 50):
            line_width = 3 if y % 250 == 0 else 1
            cv.line(image, (0, y), (width, y), color, line_width)

    @staticmethod
    def _draw_divider_segments(image, segments, color):
        for s in segments:
            x1, y1 = int(s.x1 + 0.5), int(s.y1 + 0.5)
            x2, y2 = int(s.x2 + 0.5), int(s.y2 + 0.5)
            cv.line(image, (x1, y1), (x2, y2), color=color, thickness=3)
            cv.drawMarker(
                image,
                position=(x1, y1),
                color=color,
                markerType=cv.MARKER_TRIANGLE_UP,
                markerSize=20,
                thickness=2,
            )
            cv.drawMarker(
                image,
                position=(x2, y2),
                color=color,
                markerType=cv.MARKER_TRIANGLE_DOWN,
                markerSize=20,
                thickness=2,
            )

    @staticmethod
    def _transform_point(x: float, y: float, matrix) -> (float, float):
        """Transforms a point (x, y) via an affine transformation."""
        return cv.transform(np.array([[[x, y]]]), matrix)[0][0]


def main(years: set[int], pages: list[int]) -> None:
    for volume, volume_pages in sorted(read_pages().items()):
        year = int(volume[:4])
        for page in volume_pages:
            if (page.id not in pages) and (year not in years):
                continue
            la = LayoutAnalysis(page)
            cv.imshow(f"Layout Analysis for Page {page.id}", la.debug_image())
            key = cv.waitKey(0)
            if key == ord("q"):
                return


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--pages", default="", type=parse_pages)
    ap.add_argument("--years", default="", type=parse_years)
    args = ap.parse_args()
    main(years=args.years, pages=args.pages)
