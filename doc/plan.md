# Project plan

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


## Conversion to plaintext

*Status: Partially implemented. We may need to find a better heuristic
for merging multi-line entries. Work estimate: Another 2 days of coding.*

A [script](../src/convert_hocr_to_plaintext.py) converts hOCR files
to plaintext. We store its output in the [proofread](../proofread) directory
for editing, such as manual boilerplate removal.

**Page:** In the plaintext files, the start of a new scanned page
is indicated with lines such as `# Date: 1920-12-15 Page: 25900817/119`,
where `Date` is the editorial deadline of the address book volume,
and `Page` the scanned page identifier on e-rara.ch followed by
the printed page number. If the address book page has no explicit page
number, we put the implicit page number in brackets, as in `[1]`.

**Location on page:** The plaintext files
will also include semicolon-sperated bounding boxes, for example
`# 292,1297,1011,67;1520,1319,49,34`. These indicate
which pixel areas (x, y, width, height) are part of the entry.
From this information, it would be straightforward
to generate a cropped image for each entry that highlights the
contributing areas.



## Entity mining

*Status: Not yet implemented.*

A yet to-be-written script will mine the plaintext files for family names,
given names, street names, and professions. The output needs be manually
reviewed, but this should be quick (a few hours). We will also
double-check our name lists against [Wikidata names](https://names.toolforge.org/).


## Address remapping

*Status: Not yet implemented.*

In 1882, Bern changed its addressing scheme and renumbered all
buildings.  As a side project, we should bring the [published mapping
table](https://www.e-rara.ch/bes_1/periodical/structure/3012646) into
a machine-readable form like CSV. Without this, addresses before 1882
cannot be resolved to a building. This is a side project.

## Splitting

*Status: Not yet implemented, but an earlier version can be salvaged.*

A yet to-be-written script will split the plaintext files into columns
(family name, given name, maiden name, title, profession, work/home address,
bounding boxes with location on page, etc.) and produce
Excel files for manual review. We plan to emit a separate Excel
sheet for each scanned page, since that constitutes a reasonable work
item size for human review.

Not sure yet what to do about phone numbers. We don’t care about the exact
number, but it’s interesting who got a phone line at which point in time.
Maybe we’ll just emit a column with a boolean flag to know whether or not
they had a phone.


## Human review

The Excel sheets will be reviewed by humans. The humans will correct OCR errors
(while Google Document AI is much better than the OCR system of e-rara.ch,
it’s not perfect), and make sure that the splitting into columns
(family name, given name, profession, address, etc.) is correct. The humans
will also remove ads and merge multi-line entries that our data preparation
script failed to recognize.


## Quality Assurance

*Status: Not yet implemented.*

A yet to-be-written script will extract the columns of the human-reviewed
Excel sheets and check them against the lists of known entities. Any
mismatches get reported. Either we extend the entity lists, or we correct
the data. e’ll probably put the resulting data in CSV format under version
control, in a sibling directory to the plaintext files.
