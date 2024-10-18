import io
import math
import os
import re

# this module fixes up split lines
#
# we currently do four passes:
# 1. known/hyphenated words/lines
# 2. lines ending with ',' (comma)
# 3. lines starting with a street/abbrev
# 4. lines ending w/conjunction (see JOIN_WORDS)
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

# street x/y offsets
GLUE_STREET_WITHIN = 75

STREETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'streets.csv')
STREETS = {street.strip() for street in open(STREETS_PATH, 'r')}

STREET_ABBREVS_PATH = os.path.join(os.path.dirname(__file__), '..', 'street_abbrevs.csv')
STREET_ABBREVS = {street_abbrevs.split(',')[0] for street_abbrevs in open(STREET_ABBREVS_PATH, 'r')}

LASTNAME_PATH = os.path.join(os.path.dirname(__file__), '..', 'family_names.txt')
LASTNAMES = {name.strip() for name in open(LASTNAME_PATH, 'r')}

GIVENNAME_PATH = os.path.join(os.path.dirname(__file__), '..', 'givennames.txt')
GIVENNAMES = {name.strip() for name in open(GIVENNAME_PATH, 'r')}

OCCUPATIONS_PATH = os.path.join(os.path.dirname(__file__), '..', 'occupations.csv')
OCCUPATIONS = {occ.split(',')[0] for occ in open(OCCUPATIONS_PATH, 'r')}

# If any of these words are last on a line, we join that
# line with the next one, unless the following line starts
# with a hyphen (that got actually recognized by OCR).
# The heuristic is not perfect but works pretty well.
#
# Also: If a line starts with any of these words,
# join it with the previous one, unless it's
# followed by Comp|Cie
#
# TODO(random-ao): clean up: some of these
# should be in affixes.txt and consumers of
# the list(s) should consider both
JOIN_WORDS = {
    'Aeuss.',
    'Eidg.',
    'Fa.',
    'Schweiz.',
    'Obere',
    'a.',
    'alle',
    'aller',
    'am',
    'amerik.',
    'an',
    'auch',
    'auf',
    'äuß.',
    'b.',
    'bei',
    'beim',
    'bern.',
    'bis',
    'd.',
    'das',
    'del',
    'dem',
    'den',
    'der',
    'des',
    'die',
    'Dir.',
    'durch',
    'eidg',
    'eidg.',
    'eidgen.',
    'engl.',
    'en gros',
    'et',
    'etc.',
    'f.',
    'franz.',
    'französ.',
    'für',
    'geist.',
    'geistiges',
    'i.',
    'im',
    'in',
    'Inn.',
    'Innere',
    'innere',
    'inneres',
    'Internat.',
    'Innern',
    'intern.',
    'internat',
    'internat.',
    'ital.',
    'italien.',
    'kant.',
    'kanton.',
    'mit',
    'morgens',
    'nach',
    'pens',
    'Schweizer.',
    'schweiz.',
    'schweizer.',
    'sen.',
    'sind',
    'städt.',
    'statist.',
    'topogr.',
    'u.',
    'um',
    'und',
    'Untere',
    'usw.',
    'vom',
    'vorm.',
    'vormals',
    'zu',
    'zum',
    'zur',
    'zwischen',
}


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

        # 1. this glues segments split in convert_hocr_to_plaintext.py
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
                        out.write(line_stash.replace('@@@GLUE@@@', ''))
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
                    out.write(line_stash.replace('@@@GLUE@@@', ''))
                    line_stash = ''

                out.write(line)
        os.rename(vol + '.tmp', vol)


        # 2. the following attempts to glue lines with
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

        # 3. reattach streets and occupations
        line_buffer = [line.strip() for line in open(vol, 'r')]
        known_street_frags = ['gasse', 'strasse']
        for k, line in enumerate(line_buffer):

            if line.startswith('#'): continue
            if line_buffer[k-1].startswith('#'): continue
            if line_buffer[k-1] == '': continue

            # TODO(otz): cleanup/unify once
            # done w/occ/name gluing
            first_line_seg = line.split()[0].strip()

            prev_line_txt, prev_line_pos = [x.strip() for x in line_buffer[k-1].split('#')]
            cur_line_txt, cur_line_pos = [x.strip() for x in line.split('#')]

            # take last segment of previous line and
            # first segment of current line, glue and
            # check if the result is a known occupation
            prev_first_line_seg = prev_line_txt.replace(',', ' ').split()[-1]
            cur_first_line_seg = cur_line_txt.replace(',', ' ').split()[0].strip() 
            if prev_first_line_seg + cur_first_line_seg in OCCUPATIONS:
                minted_line = f'{prev_line_txt}{cur_line_txt}  # {prev_line_pos};{cur_line_pos}'
                line_buffer[k-1] = minted_line
                line_buffer[k] = ''
                continue

            # occupations like Fournier-Sager want to keep their hyphen
            if prev_first_line_seg.endswith('-'):
                prev_first_line_seg = prev_first_line_seg[:-1]
            if prev_first_line_seg + cur_first_line_seg in OCCUPATIONS:
                minted_line = f'{prev_line_txt[:-1]}{cur_line_txt}  # {prev_line_pos};{cur_line_pos}'
                line_buffer[k-1] = minted_line
                line_buffer[k] = ''
                continue

            # take last segment of previous line and
            # first segment of current line, glue and
            # check if they are a known street/street-abbrev
            if prev_line_txt.endswith('-'):
                prev_line_txt = prev_line_txt[:-1]
            prev_first_line_seg = prev_line_txt.replace(',', ' ').split()[-1]
            cur_first_line_seg = cur_line_txt.replace(',', ' ').split()[0].strip() 
            if (prev_first_line_seg + cur_first_line_seg in STREETS or
                prev_first_line_seg + cur_first_line_seg in STREET_ABBREVS):
                minted_line = f'{prev_line_txt}{cur_line_txt}  # {prev_line_pos};{cur_line_pos}'
                line_buffer[k-1] = minted_line
                line_buffer[k] = ''
                continue

            # if first line segment is a street, street_abbrev
            # or a known street frag: glue, unless it's also
            # a lastname
            if ((first_line_seg in STREETS or
                    first_line_seg in STREET_ABBREVS or
                    first_line_seg in known_street_frags) and
                    first_line_seg not in LASTNAMES):

                prev_x, prev_y, _w, _h = [int(x) for x in prev_line_pos.split(';')[0].split(',')]

                # use max y for gluing decision
                prev_ys = []
                for pos in prev_line_pos.split(';'):
                    prev_ys.append(int(pos.split(',')[1]))
                prev_y = max(prev_ys)

                cur_x, cur_y, _w, _h = [int(x) for x in cur_line_pos.split(';')[0].split(',')]

                # note: 'e' and 's' seem bad-ocr'ed '='
                # we fix them in apply_replacements.py
                JOIN_CHARS = [':', '-', '=']

                # glue if within bounds, and prev_y < cur_y
                if ((abs(prev_x-cur_x) < GLUE_STREET_WITHIN or
                    abs(prev_y-cur_y) < GLUE_STREET_WITHIN) and
                    prev_y < cur_y):

                    # trim trailing chars
                    while any(prev_line_txt.endswith(x) for x in JOIN_CHARS):
                        prev_line_txt = prev_line_txt[:-1]

                    sep = '' if any(line.startswith(x) for x in known_street_frags) else ', '

                    # mint brand new line
                    minted_line = f'{prev_line_txt}{sep}{cur_line_txt}  # {prev_line_pos};{cur_line_pos}'
                    line_buffer[k-1] = minted_line
                    line_buffer[k] = ''

        with open(vol + '.tmp', 'w') as out:
            for line in line_buffer:
                if line != '': out.write(line + '\n')
        os.rename(vol + '.tmp', vol)

        # 4. fix lines with conjunction at the end
        line_buffer = [line.strip() for line in open(vol, 'r')]
        for k, line in enumerate(line_buffer):

            if line.startswith('#'): continue
            if line_buffer[k-1].startswith('#'): continue
            if line_buffer[k-1] == '': continue

            prev_line_txt, prev_line_pos = [x.strip() for x in line_buffer[k-1].split('#')]
            cur_line_txt, cur_line_pos = [x.strip() for x in line.split('#')]

            first_line_seg = cur_line_txt.split()[0].strip().replace(',', '')
            last_line_seg = prev_line_txt.split()[-1].strip()

            # ends in join-word and next line doesn't
            # start with either '-' or known lastname
            if (last_line_seg in JOIN_WORDS and
                not first_line_seg == '-' and
                not first_line_seg in LASTNAMES and
                not first_line_seg in GIVENNAMES):

                minted_line = f'{prev_line_txt} {cur_line_txt}  # {prev_line_pos};{cur_line_pos}'
                line_buffer[k-1] = minted_line
                line_buffer[k] = ''

        with open(vol + '.tmp', 'w') as out:
            for line in line_buffer:
                if line != '': out.write(line + '\n')
        os.rename(vol + '.tmp', vol)


if __name__ == '__main__':
    fix_conjunctions()
