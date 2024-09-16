import io
import math
import os
import re

# this module fixes up split lines
#
# we currently do two passes:
# 1. known/hyphenated words/lines
# 2. lines ending with ',' (comma)
#
# the phases are split, to avoid collision,
# even though they share the same approach
#
# TODO(random-ao): migrate '-' from
# convert_hocr_to_plaintext.py here

# drop lines shorter than this on the floor
#
# mostly affects |/1 ocr col-sep line fragments
# TODO(random-ao): passthrough housenumbers
# TODO(random-ao): check non fraktur pages
DROP_LINE_THRESHOLD = 4

# when we look for lines to glue, we
# use this x offset as confidence
# score to ensure we don't glue
# segments way off to one side
GLUE_AT_X_OFFSET = 250

# similar for y offset, but we
# also add a limit of horizontal
# dist
GLUE_AT_Y_OFFSET = 50
GLUE_AT_Y_IF_X_LESS_THAN = 500

# when we glue commas, use the following
# thresholds. they work the same as the above
COMMA_GLUE_AT_X_OFFSET = 350
COMMA_GLUE_AT_Y_OFFSET = 30
COMMA_GLUE_AT_Y_IF_X_LESS_THAN = 700

# additionally, for comma splits, we
# reorder the line if it's indented
COMMA_GLUE_REORDER_OFFSET = 30

# abandon attempt after these many lines
# (1l +/-70px)
ABANDON_STASH_AFTER_LINES = 6


def list_volumes():
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'proofread')
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.txt')]
    )

def fix_conjunctions():
    for vol in list_volumes():
        env_vl = os.environ.get('PROCESS_VOLUMES', False)
        if env_vl:
            vl = env_vl.split(',')
            if vol.split('/')[-1][:-4] not in vl:
                continue

        print('Processing conjunction fixes for %s' % vol.split('/')[-1])

        # this glues segments split in convert_hocr_to_plaintext.py
        # back together
        #
        # see below for comma-gluing, which is split out
        # to avoid conflicts (but also for clarity)
        with open(vol + '.tmp', 'w') as out:
            line_stash = ''
            for line in open(vol, 'r'):

                # pagebreak, abandon stash
                if line.startswith('#'):
                    if line_stash != '':
                        out.write(line_stash)
                        line_stash = ''
                    out.write(line)
                    continue

                # we mark up split lines with @@@GLUE@@@ in
                # convert_hocr_to_plaintext.py
                # here we pick them up, stash them for
                # iter next and then attempt to collate
                if '@@@GLUE@@@' in line:
                    line_stash = line
                    continue

                # stash available, use magic glue
                if line_stash != '':

                    # never collate lines starting w/'-'
                    if line.startswith('-'):
                        out.write(line)
                        continue

                    line_stash_txt, line_stash_pos = [x.strip() for x in line_stash.split('#')]
                    line_stash_pos_all = line_stash_pos.split(';')
                    line_stash_x, line_stash_y, _w, _h = [int(x) for x in line_stash_pos_all[0].split(',')]

                    line_txt, line_pos = [x.strip() for x in line.split('#')]
                    line_pos_all = line_pos.split(';')

                    # drop overly short lines on the floor 
                    if len(line_txt) <= DROP_LINE_THRESHOLD:
                        continue

                    # TODO(random-ao): match against last pos?
                    line_x, line_y, _w, _h = [int(x) for x in line_pos_all[0].split(',')]

                    # use superglue if the current line is close to our
                    # stash either by (x-dist) or (y-dist and same col)
                    if (abs(line_stash_x - line_x) < GLUE_AT_X_OFFSET or
                        (abs(line_stash_y - line_y) < GLUE_AT_Y_OFFSET and
                            abs(line_stash_x - line_x) < GLUE_AT_Y_IF_X_LESS_THAN)):

                        # mint new line
                        concat_line = line_stash_txt[:-11] + line_txt
                        line = f'{concat_line}  # {line_stash_pos};{line_pos}\n'

                        line_stash = ''
                else:
                    # no luck
                    out.write(line_stash)
                    line_stash = ''

                out.write(line)
        os.rename(vol + '.tmp', vol)


        # the following attempts to glue lines with
        # trailing commas back together
        with open(vol + '.tmp', 'w') as out:
            line_stash = ''
            for line in open(vol, 'r'):

                # pagebreak
                if line.startswith('#'):
                    if line_stash != '':
                        out.write(line_stash)
                        line_stash = ''
                    out.write(line)
                    continue

                line_txt, line_pos = [x.strip() for x in line.split('#')]

                # drop overly short lines on the floor 
                # TODO(random-ao) move these out to some
                # easier to find location
                if len(line_txt) <= DROP_LINE_THRESHOLD:
                    continue

                # fill stash if line ends with comma
                # we'll attempt to collate on iter next
                if line_stash == '' and line_txt.endswith(','):
                    line_stash = line
                    continue

                # stash available, try to collate
                if line_stash != '':

                    line_stash_txt, line_stash_pos = [x.strip() for x in line_stash.split('#')]
                    line_stash_pos_all = line_stash_pos.split(';')
                    line_stash_x, line_stash_y, _w, _h = [int(x) for x in line_stash_pos_all[0].split(',')]

                    # note: we match against first seg pos
                    line_pos_all = line_pos.split(';')
                    line_x, line_y, _w, _h = [int(x) for x in line_pos_all[0].split(',')]

                    # abandon dangling stash once we're
                    # these many lines down the page
                    if abs(line_y - line_stash_y) > ABANDON_STASH_AFTER_LINES * 70:
                        out.write(line_stash)
                        line_stash = ''
                        out.write(line)
                        continue

                    # glue if within bounds
                    if (abs(line_stash_x - line_x) < COMMA_GLUE_AT_X_OFFSET or
                        (abs(line_stash_y - line_y) < COMMA_GLUE_AT_Y_OFFSET and
                            abs(line_stash_x - line_x) < COMMA_GLUE_AT_Y_IF_X_LESS_THAN)):

                        # rejig line depending on seg pos
                        if (line_stash_x > line_x and
                          (abs(line_stash_y - line_y) < COMMA_GLUE_REORDER_OFFSET)):
                            line = f'{line_txt} {line_stash_txt}  # {line_pos};{line_stash_pos}\n'
                        else:
                            line = f'{line_stash_txt} {line_txt}  # {line_stash_pos};{line_pos}\n'

                        # if our newly minted line ends
                        # with ',', we'll want to look
                        # at it again on iter next
                        if line.split('#')[0].strip().endswith(','):
                            line_stash = line
                            continue
                        else:
                            line_stash = ''
                else:
                    # no luck
                    out.write(line_stash)
                    line_stash = ''

                out.write(line)
        os.rename(vol + '.tmp', vol)


if __name__ == '__main__':
    fix_conjunctions()
