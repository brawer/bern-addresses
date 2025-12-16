# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Experimental tool for layout analysis through Computer Vision.
#
# Usage:
#     venv/bin/python3 src/layout.py --pages=29210355
#     venv/bin/python3 src/layout.py --years=1863-1864,1921

from argparse import ArgumentParser
import csv
from dataclasses import dataclass
import math
from pathlib import Path

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


@dataclass
class Column:
    x: int
    y: int
    image: np.ndarray


class LayoutAnalysis(object):
    def __init__(self, page: Page):
        self.page = page
        print(page)
        self.raw_image = cv.imread(fetch_jpeg(page.id))
        self.divider_segments = self._detect_divider_segments()
        self._detect_rotation()
        self.rotated_image = cv.warpAffine(
            self.raw_image,
            self.rotation_matrix,
            self.raw_image.shape[1::-1],
            flags=cv.INTER_CUBIC,
        )
        self._detect_divider_x()
        self._detect_edges()

    def columns(self) -> list[Column]:
        top, bottom = self.top_edge, self.bottom_edge
        left, mid, right = self.left_edge, self.divider_x, self.right_edge
        return [
            self._make_column(left, top, mid - 10, bottom),
            self._make_column(mid + 10, top, right, bottom),
        ]

    def _make_column(self, x1, y1, x2, y2) -> Column:
        image = self.rotated_image[y1:y2, x1:x2]
        blurred = cv.bilateralFilter(image, 9, 50, 75)
        gray = cv.cvtColor(blurred, cv.COLOR_BGR2HLS_FULL)[:, :, 1]
        thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)[1]
        return Column(x1, y1, thresh)

    def _detect_divider_segments(self) -> list[LineSegment]:
        # For the vast majority of pages, we can automatically detect
        # the divider. But for a few cases, the algorithm fails.
        # Look up the current page in an exception table and return
        # the manually entered divider segment if the page is found.
        dividers = self._read_dividers()
        if div := dividers.get(self.page.id):
            return [div]

        segments: list[LineSegment] = []
        img = self.raw_image
        dx, dy = 600, 250
        blurred = cv.bilateralFilter(img, 5, 75, 75)
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

    def _detect_edges(self) -> None:
        blurred = cv.bilateralFilter(
            self.rotated_image, 9, 75, 75, borderType=cv.BORDER_REPLICATE
        )
        gray = cv.cvtColor(blurred, cv.COLOR_BGR2GRAY)
        height, width = gray.shape

        # Erase the vertical divider line.
        cv.line(
            gray,
            (self.divider_x, 0),
            (self.divider_x, height),
            color=(255, 255, 255),
            thickness=18,
        )

        # https://pyimagesearch.com/2021/12/01/ocr-passports-with-opencv-and-tesseract/
        rectKernel = cv.getStructuringElement(cv.MORPH_RECT, (25, 7))
        sqKernel = cv.getStructuringElement(cv.MORPH_RECT, (21, 21))
        blackhat = cv.morphologyEx(gray, cv.MORPH_BLACKHAT, rectKernel)
        grad = np.absolute(cv.Sobel(blackhat, ddepth=cv.CV_32F, dx=1, dy=0, ksize=-1))
        (minVal, maxVal) = (np.min(grad), np.max(grad))
        grad = (grad - minVal) / (maxVal - minVal)
        grad = (grad * 255).astype("uint8")
        grad = cv.morphologyEx(grad, cv.MORPH_CLOSE, rectKernel)
        thresh = cv.threshold(grad, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)[1]
        thresh = cv.morphologyEx(thresh, cv.MORPH_CLOSE, sqKernel)
        thresh = cv.erode(thresh, None, iterations=1)

        # Find the right edge of the text box. Sometimes, there are
        # manual annotations that extend the text boundary, so we probe
        # 11 stripes from the middle of the document and take the median.
        start = min(self.divider_x + 400, width)
        limit = min(start + 400, width)
        right_edges = []
        for y in list(range(0, height, height // 13))[2:-2]:
            fraction_used = np.mean(thresh[y : y + height // 13, start:limit], axis=0)
            got = np.where(fraction_used < 0.5)
            if len(got) > 0 and len(got[0] > 0):
                x = got[0][0]
                if x > 100:
                    right_edges.append(start + x)
        if len(right_edges) > 0:
            self.right_edge = min(int(np.quantile(right_edges, 0.7) + 15), width)
            column_width = self.right_edge - self.divider_x
            self.left_edge = max(0, self.divider_x - column_width)
        else:
            self.right_edge = min(self.divider_x + 850, width)
            self.left_edge = max(0, self.divider_x - 850)
        self._detect_top_bottom_edges(thresh)

    def _detect_top_bottom_edges(self, thresh: np.ndarray) -> None:
        roi = thresh[:, self.left_edge : self.right_edge].copy()
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (25, 5))
        roi = cv.morphologyEx(roi, cv.MORPH_CLOSE, kernel, iterations=7)
        height = roi.shape[0]

        # Detect the top edge. We start in a region that is likely
        # in the middle of the text, and scan towards the top until
        # we find a row that is entirely empty.
        start_y = int(height * (0.7 if self.page.is_title_page else 0.4))
        for y in range(start_y, 0, -1):
            if np.all(roi[y, :] == 0):
                break
        self.top_edge = max(y, 0)

        # Detect the bottom edge. As with the top edge, we start
        # in the middle of the text and scan towards the bottom until
        # we reach a row that does not contain any set pixels.
        for y in range(int(height * 0.7), height):
            if np.all(roi[y, :] == 0):
                break
        self.bottom_edge = min(y, height)

    def debug_image(self) -> np.ndarray:
        image = self.raw_image.copy()
        height, width, num_channels = image.shape
        self._draw_grid(image, color=(255, 128, 255))
        self._draw_divider_segments(
            image, segments=self.divider_segments, color=(128, 128, 255)
        )

        rotated_image = self.rotated_image.copy()
        self._draw_columns(rotated_image)
        if False:
            cv.rectangle(
                rotated_image,
                pt1=(self.left_edge, self.top_edge),
                pt2=(self.right_edge, self.bottom_edge),
                color=(32, 128, 32),
                thickness=6,
            )
            cv.line(
                rotated_image,
                (self.divider_x, self.top_edge),
                (self.divider_x, self.bottom_edge),
                color=(32, 128, 32),
                thickness=6,
            )

        result = np.zeros((height, width * 2, num_channels), dtype=np.uint8)
        result[0:height, 0:width] = image
        result[0:height, width : width * 2] = rotated_image
        return result

    def _draw_columns(self, image: np.ndarray) -> None:
        for c in self.columns():
            column_image = cv.cvtColor(c.image, cv.COLOR_GRAY2BGR)
            height, width = column_image.shape[:2]
            image[c.y : c.y + height, c.x : c.x + width] = column_image

    @staticmethod
    def _draw_grid(image: np.ndarray, color) -> None:
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

    @staticmethod
    def _read_dividers() -> dict[int, LineSegment]:
        global _dividers
        if len(_dividers) > 0:
            return _dividers
        path = Path(__file__) / ".." / ".." / "data" / "dividers.csv"
        with open(path.resolve()) as fp:
            for r in csv.DictReader(fp):
                page_id = int(r["PageID"])
                x1, y1 = float(r["X1"]), float(r["Y1"])
                x2, y2 = float(r["X2"]), float(r["Y2"])
                _dividers[page_id] = LineSegment(x1, y1, x2, y2)
        return _dividers


_dividers: dict[int, LineSegment] = {}


def main(years: set[int], pages: list[int]) -> None:
    for volume, volume_pages in sorted(read_pages().items()):
        year = int(volume[:4])
        for page in volume_pages:
            if (page.id not in pages) and (year not in years) and (years or pages):
                continue
            la = LayoutAnalysis(page)
            title = f"Layout Analysis for Page {page.id}"
            cv.imshow(f"Layout Analysis for Page {page.id}", la.debug_image())
            cv.setMouseCallback(title, _on_event)
            key = cv.waitKey(0)
            if key == ord("q"):
                return
            if key == ord("s"):
                for i, col in enumerate(la.columns()):
                    cv.imwrite(f"col-{page.id}-{i + 1}.png", col.image)
            cv.destroyAllWindows()


def _on_event(event, x, y, _flags, _param):
    if event == cv.EVENT_LBUTTONDOWN:
        print(f"{x},{y}")


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--pages", default="", type=parse_pages)
    ap.add_argument("--years", default="", type=parse_years)
    args = ap.parse_args()
    main(years=args.years, pages=args.pages)
