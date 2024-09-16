# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Sort entries on each page by (column, y).

import io
import os


# defines what offset to use for col identification
#
# note: all current pages are 2000 wide
COL_X_MIN_WIDTH = 850

# Helper that collects the entries on the same page,
# and writes them out in sorted order.
class Page(object):
    def __init__(self):
        self.entries = []

    def add_entry(self, line):
        text, pos = [x.strip() for x in line.split("#")]
        x, y, width, height = [int(x) for x in pos.split(";")[0].split(",")]
        if x <= COL_X_MIN_WIDTH:
            column = 1
        else:
            column = 2
        self.entries.append((column, y, line))

    def write(self, out):
        for _column, _y, line in sorted(self.entries):
            out.write(line)
            out.write("\n")


# Fixes the line order in a given address book volume.
def fix_line_order(vol):
    out = io.StringIO()
    page = None
    for line in open(vol, "r"):
        line = line.strip()
        if line[0] == "#":
            if page:
                page.write(out)
            out.write(line + "\n")
            page = Page()
        else:
            page.add_entry(line)
    page.write(out)
    tmp = vol + ".tmp"
    with open(tmp, "w") as outfile:
        outfile.write(out.getvalue())
    os.rename(tmp, vol)


# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )


if __name__ == "__main__":
    for vol in list_volumes():

        env_vl = os.environ.get('PROCESS_VOLUMES', False)
        if env_vl:
            vl = env_vl.split(',')
            if vol.split('/')[-1][:-4] not in vl:
                continue

        print('Updating line order in %s' % vol.split('/')[-1])
        fix_line_order(vol)
