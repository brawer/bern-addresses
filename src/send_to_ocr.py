# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Fetch JPEG files from e-rara.ch, send them to Google Document AI
# for Optical Character Recognition, and store the result in hOCR format.
# The e-rara.ch platform offers pre-generated OCR results for download,
# but the quality is rather low. Therefore we re-OCR the files.
#
# See https://github.com/brawer/bern-addresses/issues/347 for possibly
# using another OCR engine than Google Document AI.

from argparse import ArgumentParser
import csv
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import cv2 as cv
import numpy as np

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1
from google.cloud.documentai_v1.services.document_processor_service.client import (
    DocumentProcessorServiceClient,
)
from google.cloud.documentai_v1.types.processor import Processor

from layout import Column, LayoutAnalysis
from utils import Page, fetch_jpeg, parse_pages, parse_years, read_pages


# The following are public IDs, not access credentials.
GOOGLE_PROJECT_ID = "adressbuch-bern"
GOOGLE_OCR_PROCESSOR_ID = "8383e802db93690c"


@dataclass
class Line:
    text: str
    page: int
    column: int
    x: int
    y: int
    width: int
    height: int


REPLACEMENTS = {
    "ẵ": "ä",
    "gaffe": "gaſſe",
    "gasse": "gaſſe",
    "I.": "J.",
    "Käshdir": "Käshdlr",
    "Megg": "Metzg",
    "Mezg": "Metzg",
    "Nent": "Rent",
    "plazg": "platzg",
    "plagg": "platzg",
    "Räfich": "Käfich",
    "Regt.": "Negt.",
    "Schlsfr": "Schlſſr",
    "sc": "ſc",
    "st": "ſt",
    "sp": "ſp",
    "ss": "ſſ",
}


class GoogleOCR(object):
    def __init__(self, location: str, project_id: str, processor_id: str):
        self.client = self._make_client(location)
        self.processor = self._make_processor(location, project_id, processor_id)
        self.at_sign = self._read_at_sign()

    def process(self, page: Page) -> list[Line]:
        la = LayoutAnalysis(page)
        lines: list[Line] = []
        is_fraktur = int(page.date[:4]) <= 1879
        for col_index, col in enumerate(la.columns):
            img = self._insert_at_signs(col)
            ok, png = cv.imencode(".png", img)
            if not ok:
                raise ValueError(
                    f"could not encode column {col_index} of page {page.id}"
                )
            doc = documentai_v1.RawDocument(
                content=png.tobytes(), mime_type="image/png"
            )
            req = documentai_v1.ProcessRequest(
                name=self.processor.name, raw_document=doc
            )
            result = self.client.process_document(request=req)
            for line in result.document.pages[0].lines:
                ll = line.layout
                segments = [
                    result.document.text[s.start_index : s.end_index]
                    for s in ll.text_anchor.text_segments
                ]
                text = self._clean_text("".join(segments).strip(), is_fraktur)
                if not text:
                    continue
                x = min(v.x for v in ll.bounding_poly.vertices)
                y = min(v.y for v in ll.bounding_poly.vertices)
                width = max(v.x for v in ll.bounding_poly.vertices) - x
                height = max(v.y for v in ll.bounding_poly.vertices) - y
                lines.append(
                    Line(
                        text,
                        page.id,
                        col_index + 1,
                        col.x + x,
                        col.y + y,
                        width,
                        height,
                    )
                )
        return lines

    def _make_client(self, location) -> DocumentProcessorServiceClient:
        endpoint = f"{location}-documentai.googleapis.com"
        opts = ClientOptions(api_endpoint=endpoint)
        return documentai_v1.DocumentProcessorServiceClient(client_options=opts)

    def _make_processor(
        self, location: str, project_id: str, processor_id: str
    ) -> Processor:
        processor_name = self.client.processor_path(project_id, location, processor_id)
        req = documentai_v1.GetProcessorRequest(name=processor_name)
        return self.client.get_processor(request=req)

    def _read_at_sign(self) -> np.ndarray:
        # https://github.com/brawer/bern-addresses/issues/342
        path = Path(__file__) / ".." / "at_sign.png"
        img = cv.imread(path.resolve())
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        return cv.threshold(gray, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)[1]

    def _insert_at_signs(self, col: Column) -> np.array:
        # https://github.com/brawer/bern-addresses/issues/342
        img = col.image.copy()
        at_h, at_w = self.at_sign.shape[:2]
        for dash in col.dashes:
            x1, y1 = int(dash.x1 + 0.5), int(dash.y1 + 0.5)
            x2, y2 = int(dash.x2 + 0.5), int(dash.y2 + 0.5)
            cv.line(img, (x1, y1), (x2, y2), color=(255,), thickness=7)
            at_x = x1
            at_y = min(y1, y2) - (at_h // 2)
            img[at_y : at_y + at_h, at_x : at_x + at_w] = self.at_sign
        return img

    def _clean_text(self, text: str, fraktur: bool) -> str:
        if text[0] == "@":
            text = "— " + text[1:].strip()
        if fraktur and text[-1] in ("-", ":"):
            text = text[:-1].strip() + "\u2e17"
        text = re.sub(r"\.([0-9A-ZÄÖÜ])", lambda m: ". " + m.group(1), text)
        text = re.sub(
            r"([0-9] [a-z][,.]?)", lambda m: m.group(1).replace(" ", ""), text
        )
        for a, b in REPLACEMENTS.items():
            text = text.replace(a, b)
        return text


def main(years: set[int], pages: list[int]) -> None:
    ocr = GoogleOCR(
        location="eu",
        project_id=GOOGLE_PROJECT_ID,
        processor_id=GOOGLE_OCR_PROCESSOR_ID,
    )
    for volume, volume_pages in sorted(read_pages().items()):
        year = int(volume[:4])
        out, writer = None, None
        for page in volume_pages:
            if (page.id not in pages) and (year not in years):
                continue
            if out is None:
                path = Path(__file__) / ".." / ".." / "ocr-lines" / (page.date + ".csv")
                out = open(path.resolve(), "w")
                writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(
                    ["PageID", "Column", "X", "Y", "Width", "Height", "Text"]
                )
            lines = ocr.process(page)
            for line in lines:
                cols = [
                    str(c)
                    for c in (
                        line.page,
                        line.column,
                        line.x,
                        line.y,
                        line.width,
                        line.height,
                    )
                ]
                cols.append(line.text)
                writer.writerow(cols)
        if out is not None:
            out.close()


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--pages", default="", type=parse_pages)
    ap.add_argument("--years", default="", type=parse_years)
    args = ap.parse_args()
    if args.years or args.pages:
        main(years=args.years, pages=args.pages)
    else:
        print("either --pages or --years must be specified", file=sys.stderr)
