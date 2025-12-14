# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Internal utility functions.

from collections import namedtuple
import csv
import os
from pathlib import Path
import urllib.request


Page = namedtuple("Page", "id date")

def fetch_jpeg(page_id: int) -> Path:
    """
    Fetch the JPEG image for a single page from e-rara.ch.

    If the image is already in cache, the cached content is returned
    without re-downloading it over the internet.

    Args:
        page_id: Numeric ID of the page, such as 29210874
        for https://www.e-rara.ch/bes_1/periodical/pageview/29210874.

    Returns:
        Path to the fetched JPEG file on local disk.
    """
    filepath = os.path.join("cache", "images", f"{page_id}.jpg")
    if not os.path.exists(filepath):
        os.makedirs(os.path.join("cache", "images"), exist_ok=True)
        url = f"https://www.e-rara.ch/download/webcache/2000/{page_id}"
        with urllib.request.urlopen(url) as u:
            img = u.read()
        # Write to a temp file, followed by (atomic) rename, so we never
        # have partially written files in the final location, even if
        # the process crashes while writing out the file.
        with open(filepath + ".tmp", "wb") as f:
            f.write(img)
        os.rename(filepath + ".tmp", filepath)
    return Path(filepath)


def read_pages():
    pages = {}
    path = Path(__file__) / ".." / "pages.csv"
    with open(path.resolve()) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date, page_id = row["Date"], int(row["PageID"])
            p = Page(page_id, date)
            pages.setdefault(date, []).append(p)
    return pages
