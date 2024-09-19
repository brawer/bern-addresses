# Bern Address Book

## Setup

```sh
[SEMI-DEPRECATED]
$ git clone https://github.com/brawer/bern-addresses.git
$ cd bern-addresses
$ python3 -m venv venv
$ venv/bin/pip3 install -r requirements.txt
$ venv/bin/python3 src/fetch.py
```

## Input Pipeline

```sh
git restore proofread/
python3 src/convert_hocr_to_plaintext.py
python3 src/cleanup/blackhole_lines.py
python3 src/cleanup/fix_line_order.py
python3 src/cleanup/sanitize.py
python3 src/cleanup/fix_conjunctions.py
python3 src/cleanup/apply_replacement.py
python3 src/cleanup/fix_indentation.py
```

### Processing specific volumes
Use `PROCESS_VOLUMES='1862-07-31,1877-03-31'` to only process a subset of volumes.
