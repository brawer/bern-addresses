# Work plan

## Finding content pages

**Chapters**: The [historic address books of Bern](https://www.e-rara.ch/bes_1/periodical/structure/1395833) are split into chapters. We wanted to focus on the directory of
residents, which is just one or (starting 1938) two chapters of the yearly volume. From the table of contents of each volume, we created a
[list of chapters](../src/chapters.csv) with columns `Date`, `Year` `VolumeID`, `ChapterTitle` and `ChapterID`. The date is the editorial deadline of the volume, which was typically stated in the foreword, an appendix, and which we
manually checked for each volume.

**Full-page ads**: Among the content pages, there occasionally are
[full-page ads](https://www.e-rara.ch/bes_1/periodical/pageview/25703771).
We manually created a [denylist with 407 ads pages](../src/ads.txt).

**Content pages**: We created a [list of content pages](../src/pages.csv).
The `Date`column is the editorial deadline of the
volume (same as in the chapters list), such as `1893-05-31`;
the `PageID` column is the numeric ID for the scalled page on e-rara.ch,
such as [3014457](https://www.e-rara.ch/bes_1/periodical/pageview/3014457);
`PageLabel` is the page printed in the address book, such as `286`.
In some years, the first page of a chapter did not have an explicit page
number on the page ([example](https://www.e-rara.ch/bes_1/periodical/pageview/26035008));
in those cases, we put into `PageLabel` the implicit page number in brackets,
such as `[1]`.


## Re-OCRing

In a first iteration, we worked with the OCR files hosted on e-rara.ch
([example](https://www.e-rara.ch/bes_1/download/fulltext/alto3/29210592)).
However, their OCR quality turned out to quite terrible, requiring lots of
manual correction. We therefore re-OCRed all content  pages with
[Google Document AI](https://cloud.google.com/document-ai?hl=en) using
the [send_to_ocr.py](../src/send_to_ocr.py) script, which stores
the conversion result to local disk, both in [DocumentAI JSON](https://cloud.google.com/document-ai/docs/handle-response) and [hOCR](http://kba.github.io/hocr-spec/1.2/) format.


## TODO: Elaborate work plan
