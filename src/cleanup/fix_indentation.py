# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT


import io
import os


# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )


def fix_indentation():
    gnpath = os.path.join(os.path.dirname(__file__), 'frequent_given_names.txt')
    # TODO(random-ao): generate a freq list, family_names.txt/.. are too broad
    lnpath = os.path.join(os.path.dirname(__file__), 'frequent_last_names.txt')
    givennames = {name.strip() for name in open(gnpath, 'r')}
    lastnames = {name.strip() for name in open(lnpath, 'r')}
    for vol in list_volumes():
        with open(vol + '.tmp', 'w') as out:
            for line in open(vol, 'r'):
                line = line.strip()
                if not line:
                    continue

                # split by whitespace (original approach)
                # and by comma, then see if the first
                # segment is a family name, followed
                # by a givenname segment
                # TODO(random-ao): 2 splits is suboptimal
                # check if needed, also strips too much,..

                ws_splits = line.split()
                if (ws_splits[0].strip() in lastnames
                    and ws_splits[1].strip() in givennames):
                        out.write(line + '\n')
                        continue

                comma_splits = line.split(',')
                if (comma_splits[0].strip() in lastnames
                    and comma_splits[1].strip() in givennames):
                        out.write(line + '\n')
                        continue

                # TODO(random-ao): add two more checks
                # 1. if 1st is lastname and 2nd is job
                # 2. if 1st is lastname and 2nd is street

                # check if first segment is known givenname
                if (ws_splits[0].strip() in givennames
                    or comma_splits[0].strip() in givennames):
                        out.write('- ' + line + '\n')
                        continue

                # no match found
                out.write(line + '\n')
        os.rename(vol + '.tmp', vol)


if __name__ == "__main__":
    fix_indentation()
