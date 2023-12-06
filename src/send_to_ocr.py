# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Fetch JPEG files from e-rara.ch, send them to Google Document AI
# for Optical Character Recognition, and store the result in hOCR format.
# The e-rara.ch platform offers pre-generated OCR results for download,
# but the quality is rather low. Therefore we re-OCR the files.

import csv
import os
import urllib.request

from google.api_core.client_options import ClientOptions
from google.cloud import documentai, documentai_toolbox

# The following are public IDs, not access credentials.
GOOGLE_PROJECT_ID = "datafy-407114"
GOOGLE_OCR_PROCESSOR_ID = "6fc8e1cdff22fd02"


# Returns a map like {"1860-02-01": [29210065, 29210066, ...], ...}
# that tells which volume contains what page IDs.
def read_pages():
    pages = {}
    with open("src/pages.csv") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date, pageid = row["Date"], int(row["PageID"])
            pages.setdefault(date, []).append(pageid)
    return pages


# Fetch the JPEG image for a single page from e-rara.ch.
def fetch_jpeg(pageid):
    url = f"https://www.e-rara.ch/download/webcache/2000/{pageid}"
    with urllib.request.urlopen(url) as u:
        img = u.read()
    return img


# Fetch a single page from e-rara.ch, send it to Google Document AI for OCR,
# and store the output in hOCR format on local disk. If the hOCR output file
# is already present, this function does nothing.
def call_ocr(client, pageid):
    outpath = os.path.join("cache", "hocr", f"{pageid}.hocr")
    if os.path.exists(outpath):
        return
    print(f"fetching {pageid}")
    jpeg = fetch_jpeg(pageid)
    raw_doc = documentai.RawDocument(content=jpeg, mime_type="image/jpeg")
    process_options = documentai.ProcessOptions(
        ocr_config=documentai.OcrConfig(
            enable_image_quality_scores=True,
            enable_symbol=True,
            hints=documentai.OcrConfig.Hints(language_hints=["de"]),
        ),
    )
    p = client.processor_path(GOOGLE_PROJECT_ID, "eu", GOOGLE_OCR_PROCESSOR_ID)
    request = documentai.ProcessRequest(
        name=p,
        raw_document=raw_doc,
        field_mask=None,
        process_options=process_options,
    )
    print(f"ocr-ing {pageid}")
    result = client.process_document(request=request)
    doc = result.document

    json_path = os.path.join("cache", "documentai", f"{pageid}.json")
    with open(json_path, "w") as t:
        t.write(documentai.Document.to_json(doc))

    tbdoc = documentai_toolbox.document.Document.from_document_path(json_path)
    hocr = tbdoc.export_hocr_str(title=f"{pageid}")
    with open(outpath + ".tmp", "w") as out:
        out.write(hocr)
    os.rename(outpath + ".tmp", outpath)


if __name__ == "__main__":
    for dirname in ["documentai", "hocr"]:
        path = os.path.join("cache", dirname)
        if not os.path.exists(path):
            os.makedirs(path)
    opts = ClientOptions(api_endpoint="eu-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    pages = read_pages()
    for date, pageids in sorted(pages.items()):
        print(f"processing {date}, {len(pageids)} pages")
        for p in pageids:
            call_ocr(client, p)
