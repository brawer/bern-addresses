# Data files

This directory contains various data files for the address book project.


## Address reform 1882

In 1882, the city of Bern had an address reform. Many house numbers changed,
and some streets were renamed as well. The file `address_reform_1882.csv`
contains a mapping table for this reform.

To verify the mapping, We checked for each “new” address whether it
still existed in the federal buildings register (Eidg. Gebäude- und
Wohnungsregister, GWR) as of 2025.

* If the post-1882 address still existed in 2025, the status field is set
  to `OK`. The address mapping entry is likely correct.
  For example, the pre-1882 address `Gerbernlaube 144` changed in 1882 to
  `Theaterplatz 6`; in the 2025 buildings register, this address still
  existed.

* If the post-1882 *street name* still existed in 2025, but the house
  number does not exist, the status field is set to `Unbekannte Hausnummer`.
  Perhaps the house might have been torn down between 1882 and 2025?
  Or perhaps the mapping table, which was printed in 1882, indicated
  a new address that never actually existed. It could also be an OCR
  error. Such entries need further research.

* If the post-1882 *street name* did not exist in 2025, the status field
  is set to `Unbekannte Strasse`. Again, such entries need further
  research.


## Divider lines

The file `dividers.csv` contains an exception list for the detection of
vertical divider lines in [../src/layout.py](src/layout.py).  For
most pages, the Computer Vision algorithm works fine, but occasionally
it fails.  If a page is listed in this file, the (manually entered) pixel
coordinates of its divider line are used instead of the algorithmically
determined position.
