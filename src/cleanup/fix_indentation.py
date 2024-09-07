# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT


import io
import math
import os

# semi-arbitrary value, to optimize indenting detection
MAX_INDENT_SHIFT = 200

# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )

def trim(s):
    return s.strip().replace(',', '')

def fix_indentation():
    gnpath = os.path.join(os.path.dirname(__file__), 'frequent_given_names.txt')
    # TODO(random-ao): generate a freq list, family_names.txt/.. are too broad
    lnpath = os.path.join(os.path.dirname(__file__), 'frequent_last_names.txt')
    occpath = os.path.join(os.path.dirname(__file__), '..', 'occupations.csv')
    givennames = {name.strip() for name in open(gnpath, 'r')}
    lastnames = {name.strip() for name in open(lnpath, 'r')}
    occupations = {occ.split(',')[0] for occ in open(occpath, 'r')}

    for vol in list_volumes():
        print('Processing indentation fixes for %s' % vol.split('/')[-1])

        with open(vol + '.tmp', 'w') as out:

            # store first 3 chars of last line
            # so we can look around
            last_prefix = ''

            last_x = 0
            indent_toggle = False
            for line in open(vol, 'r'):
                line = line.strip()
                if not line:
                    continue

                if line[0] == '#':
                    last_x = 0 # new page, new luck
                    out.write(line + '\n')
                    continue

                # skip if indented already
                if line[0] == '-':
                    last_prefix = line[:3]
                    out.write(line + '\n')
                    continue

                x = int(line.split('#')[1].split(";")[0].split(",")[0])
                if last_x == 0: last_x = x

                # col break
                if abs(last_x - x) > MAX_INDENT_SHIFT: #200:
                    last_x = x

                # avoid bulging
                if x < last_x:
                    last_x = x

                # if we're too close, shift cursor, to follow warped scans
                if math.isclose(x, last_x, rel_tol=0.2):
                    indent_toggle = False
                    last_x = x
                else: indent_toggle = True

                if indent_toggle:
                    if (trim(line.split()[0]) in givennames or
                        trim(line.split(',')[0]) in givennames):
                        out.write(f'- {line}\n')
                        continue

                # split by whitespace (original approach)
                # and by comma, then see if the first
                # segment is a family name, followed
                # by a givenname segment
                # TODO(random-ao): 2 splits is suboptimal
                # check if needed, also strips too much,..

                ws_splits = line.split()
                if (trim(ws_splits[0]) in lastnames
                    and trim(ws_splits[1]) in givennames):

                        # if the previous line started with
                        # the same char, this might be a
                        # lastname
                        if last_prefix[0] == trim(ws_splits[0])[0]:
                            out.write(line + '\n')
                            last_prefix = line[:3]
                            continue

                        # if last line was indented and the
                        # same char, it might be a givenname
                        if last_prefix[2] == trim(ws_splits[0])[0]:
                            line_out = '- %s\n' % line
                            out.write(line_out)
                            last_prefix = line_out[:3]
                            continue

                        # if the next segment is a known
                        # occupation, it might be a givenname
                        if line.split(',')[1].strip() in occupations:
                            line_out = '- %s\n' % line
                            out.write(line_out)
                            last_prefix = line_out[:3]
                            continue

                        last_prefix = line[:3]
                        out.write(line + '\n')
                        continue

                # TODO(random-ao): refactor, do the same as for ws_splits
                comma_splits = line.split(',')
                if (trim(comma_splits[0]) in lastnames
                    and trim(comma_splits[1]) in givennames):
                        if last_prefix[2] == trim(ws_splits[0])[0]:
                            out.write('- ' + line + '\n')
                            last_prefix = '- ' + line[0]
                            continue
                        last_prefix = line[:3]
                        out.write(line + '\n')
                        continue

                # TODO(random-ao): add one more check
                # - if 1st is lastname and 2nd is street

                # check if first segment is known givenname
                if (trim(ws_splits[0]) in givennames
                    or trim(comma_splits[0]) in givennames):
                        line_out = '- %s\n' % line
                        out.write(line_out)
                        last_prefix = line_out[:3]
                        continue

                # no match found
                last_prefix = line[:3]
                out.write(line + '\n')
        os.rename(vol + '.tmp', vol)


if __name__ == "__main__":
    fix_indentation()
