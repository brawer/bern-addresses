import os
import re
import statistics
import csv

from difflib import SequenceMatcher
from cleanup.fix_conjunctions import JOIN_WORDS

# slider to decide how many unknown fragments we
# accept in a line
#
# TODO(random-ao): greedy, needs refinement
ACCEPT_MAX_UNKNOWN_FRAGS = 0

# accept lines which are this much similar to original line
SEQUENCE_MATCH_THRESHOLD = .95

# print some debug information to stdout
DEBUG_TO_STDOUT = False

# write unknown fragment lists
# if True, writes:
# unknown-lastnames.csv: all unknown fragments encountered
# unknown-givennames.csv: unknown 2nd pos fragments
# unknown-fragments.csv: unknown 1st pos fragments
# csvs are ordered by freq of occurrence
WRITE_UNKNOWN_FRAGMENT_LIST = True

# load lookup tables
AFFIXES_PATH = os.path.join(os.path.dirname(__file__), 'affixes.txt')
AFFIXES = {affix.rstrip() for affix in open(AFFIXES_PATH, 'r')}

COMPANIES_PATH = os.path.join(os.path.dirname(__file__), 'companies.csv')
COMPANIES = {c.split(',')[0].strip() for c in open(COMPANIES_PATH, 'r')}

GIVENNAME_PATH = os.path.join(os.path.dirname(__file__), 'givennames.txt')
GIVENNAMES = {name.strip() for name in open(GIVENNAME_PATH, 'r')}

LASTNAME_PATH = os.path.join(os.path.dirname(__file__), 'family_names.txt')
LASTNAMES = {name.strip() for name in open(LASTNAME_PATH, 'r')}

OCCUPATIONS_PATH = os.path.join(os.path.dirname(__file__), 'occupations.csv')
OCCUPATIONS = {occ.split(',')[0] for occ in open(OCCUPATIONS_PATH, 'r')}

POIS_PATH = os.path.join(os.path.dirname(__file__), 'pois.csv')
POIS = {street_abbrevs.split(',')[0] for street_abbrevs in open(POIS_PATH, 'r')}

STREETS_PATH = os.path.join(os.path.dirname(__file__), 'streets.csv')
STREETS = {street.strip() for street in open(STREETS_PATH, 'r')}

STREET_ABBREVS_PATH = os.path.join(os.path.dirname(__file__), 'street_abbrevs.csv')
STREET_ABBREVS = {street_abbrevs.split(',')[0] for street_abbrevs in open(STREET_ABBREVS_PATH, 'r')}

TITLES_PATH = os.path.join(os.path.dirname(__file__), 'titles.csv')
TITLES = {title.split(',')[0] for title in open(TITLES_PATH, 'r')}


def list_volumes():
    path = os.path.join(os.path.dirname(__file__), '..', 'proofread')
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.txt')]
    )

# splits line into list of frags
def explode(line):
    line = line.split('#')[0]
    line = line.replace(',', ' ')
    return line.split()

def islastname(frag):
    # allow (Schmitter)
    # TODO: allow Wüterich-Gaudard
    frag = re.sub('[()]', '', frag)
    if not frag: return False

    # consecutive lines use '-'
    # as placeholder
    if frag[0] == '-': return True

    # check in family_names.txt
    if frag in LASTNAMES: return True

    return False

def isgivenname(frag):
    # check in givennames.txt
    if frag in GIVENNAMES: return True

    return False

# TODO(random-ao): use closest matches via difflib
def isoccupation(frag):
    # first check in occupations.csv
    # then in companies.csv
    if frag in OCCUPATIONS: return True
    if frag in COMPANIES: return True
    return False

# TODO(random-ao): split out locations,
# like Länggasse into pois, or better,
# neighborhoods/districts, then add col
def isstreet(frag):
    # normalize ß
    frag = frag.replace('ß', 'ss')
    # allow (street)
    frag = re.sub('[()]', '', frag)

    # check in streets.csv
    # then in street_abbrevs.csv
    # lastly in pois.csv
    if frag in STREETS: return True
    if frag in STREET_ABBREVS: return True
    if frag in POIS: return True

    return False

def ishousenumber(frag):
    # allow 12d
    if re.match('^\d{1,3}[a-z]{0,1}$', frag): return True

    # and single letter frags (we'll only re-attach them,
    # if they are at the correct offset)
    if re.match('^[a-z]{1}$', frag): return True

    return False

def istitle(frag):
    # check titles.csv
    if frag in TITLES: return True

    return False

def isjoinword(frag):
    # check JOIN_WORDS from fix_conjunctions.py
    if frag in JOIN_WORDS: return True

    return False

# we suffix some frags, like 'd.' with their pos,
# to allow >1 identical frags, this is just
# a convenience function to centralize stripping
def striphash(val):
    return val[:val.rfind('-')]

# compares provided frag to givennames
# after stripping hash 
def gnisln(frag, givennames):
    for gn in givennames:
        if striphash(gn) == frag: return True
    return False

# check if frag is affix
def isaffix(frag):
    # check affixes.txt
    if frag in AFFIXES: return True
    return False

# get housenumber fragments at offset, if any
def gethousenumber(frags, offset):
    hn = []
    for frag in frags.items():
        if frag[1] == offset:
            hn.append(frag[0])
            offset += 1
    return (''.join(hn), offset)

# goes through (unmatched) fragments, returns
# string of frags at offset and list of
# remaining frags
def vacuum(frags, offset):
    if len(frags) == 0: return (offset, '', [])

    # sort by offset
    frags.sort(key = lambda x: x[1])

    ret = []
    ret_frags = []
    for frag in frags:
        if frag[1] == offset:
            ret.append(frag[0])
            offset += 1
        else:
            ret_frags.append(frag)

    return (offset, ' '.join(ret), ret_frags)

# attempts to re-assemble the line, cleanly
# separated by commas, for later split.py segmentation
#
# segments: ln, fn, occ, street + num
def joiner(matched_fragments, num_identified):

    # segment position
    offset = 0

    # buffer to attach segments to
    out = ''

    # naive confidence score:
    # 1=good
    # -.1 for every uncertain rejig
    score = 0

    # buffer for segments we fail to attach
    # at given offset; we remember them to
    # reuse on occasion
    unattached_fragments = []

    # seed buffers with joinwords, titles, affixes
    #
    # optionally, if ACCEPT_MAX_UNKNOWN_FRAGS > 0,
    # add a sprinkle of segments we couldn't identify
    for pos, (word, spos) in enumerate(matched_fragments['joinword'].items()):
        unattached_fragments.append((striphash(word), spos))

    # TODO(random-ao): consider separate col for title
    for pos, (title, spos) in enumerate(matched_fragments['title'].items()):
        unattached_fragments.append((title, spos))

    for pos, (title, spos) in enumerate(matched_fragments['affix'].items()):
        unattached_fragments.append((title, spos))

    if len(matched_fragments['unknown']) <= ACCEPT_MAX_UNKNOWN_FRAGS:
        max_unknowns_consumed = 0
        for pos, (title, spos) in enumerate(matched_fragments['unknown'].items()):
            unattached_fragments.append((title, spos))
            max_unknowns_consumed += 1
            if max_unknowns_consumed >= ACCEPT_MAX_UNKNOWN_FRAGS: break

    # start constructing output line: lastname
    lname_out = []
    lname_score = 1
    if len(matched_fragments['lastnames']) == 0:
        lname_out.append('-')
    else:
        for pos, (lname, spos) in enumerate(matched_fragments['lastnames'].items()):

            # see if there's anything to absorb at offset
            offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
            if v_cont != '':
                lname_score -= 0.1
                lname_out.append(v_cont)

            # if our frag position is > offset, append
            # it to unattached_fragments, for later use
            if spos > offset:
                unattached_fragments.append((lname, spos))
                continue

            lname_out.append(lname)
            offset += 1

    out = ' '.join(lname_out) + ', '

    # next: givenname
    fname_out = []
    fname_score = 1
    if len(matched_fragments['givennames']) == 0:
        fname_score -= .1

    for pos, (fname, spos) in enumerate(matched_fragments['givennames'].items()):
        # absorb?
        offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
        if v_cont != '':
            fname_score -= .1
            fname_out.append(v_cont)

        # if our frag position is > offset, append
        # it to unattached_fragments, for later use
        if spos > offset:
            unattached_fragments.append((fname, spos))
            continue

        fname_out.append(striphash(fname))
        offset += 1

    out += ' '.join(fname_out) + ', '

    # next: occupations
    occ_out = []
    occ_score = 1
    if len(matched_fragments['occupations']) == 0:
        occ_score -= .1

        # absorb titles,.. if any at pos
        offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
        if v_cont != '':
            occ_out.append(v_cont)
    else:
        for pos, (occ, spos) in enumerate(matched_fragments['occupations'].items()):

            # absorb?
            offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
            if v_cont != '':
                occ_out.append(v_cont)

            # if our frag position is > offset, append
            # it to unattached_fragments, for later use
            if spos > offset:
                unattached_fragments.append((occ, spos))
                continue

            occ_out.append(occ)
            offset += 1

            offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
            if v_cont != '':
                occ_out.append(v_cont)

    out += ' '.join(occ_out) + ', '

    # next: street + housenumber
    street_out = []
    street_score = 1
    if len(matched_fragments['streets']) == 0:
        street_score -= .1

    for pos, (street, spos) in enumerate(matched_fragments['streets'].items()):
        # absorb?
        offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
        if v_cont != '':
           out += v_cont

        # if our frag position is > offset, append
        # it to unattached_fragments, for later use
        if spos > offset:
            unattached_fragments.append((street, spos))
            continue

        street_out.append(street)
        offset += 1

        # see if there's a housenumber at offset
        hn, offset = gethousenumber(matched_fragments['housenumber'], offset)
        if hn != '':
            street_out.append(hn)

        # absorb?
        offset, v_cont, unattached_fragments = vacuum(unattached_fragments, offset)
        if v_cont != '':
            street_out.append(v_cont)

        score = statistics.mean([
            lname_score,
            fname_score,
            occ_score,
            street_score
        ])

    out += ' '.join(street_out) # eol

    return (out, score)


# processes vol by vol (gated by PROCESS_VOLUMES)
# explodes every line, matches up segments against
# known good segments and reassembles the line
def inspect():

    # these are synthetic buffers to
    # keep tabs of unidentified segments.
    #
    # synthetic because heuristics are cheap:
    # missing_lastnames = 1st seg, unknown lastname
    # missing_givennames = 2nd seg, unknown givenname
    # unknown_fragments = any fragment we can't identify
    missing_lastnames = {}
    missing_givennames = {}
    unknown_fragments = {}

    # total lines processed
    total_lines = 0

    # lines where we were able to identifiy
    # one segment for each of lname, fname, occ, street
    known_good = 0

    # lines where we didn't achieve this
    known_bad = 0

    # count lines above SEQUENCE_MATCH_THRESHOLD
    seq_ok = 0

    for vol in list_volumes():
        env_vl = os.environ.get('PROCESS_VOLUMES', False)
        if env_vl:
            vl = env_vl.split(',')
            if vol.split('/')[-1][:-4] not in vl:
                continue

        print('Inspecting %s' % vol.split('/')[-1])

        # keep lines in a dedicated buffer for now
        new_line_buffer = []

        for line in open(vol, 'r'):

            total_lines += 1

            if line.startswith('#'):
                new_line_buffer.append(line)
                continue

            scored_line = {}
            scored_line.setdefault('affix', {})
            scored_line.setdefault('givennames', {})
            scored_line.setdefault('housenumber', {})
            scored_line.setdefault('joinword', {})
            scored_line.setdefault('lastnames', {})
            scored_line.setdefault('occupations', {})
            scored_line.setdefault('streets', {})
            scored_line.setdefault('title', {})
            scored_line.setdefault('unknown', {})

            line_fragments = explode(line)

            # remember number of frags, to compare
            # to total_found later
            total_fragments = len(line_fragments)
            total_found = 0

            # iterate through frags, try to identify them
            #
            # note: we accept most frags to be identified
            # as multiple types; we adjust for this later
            # by only adding known frags in sequence
            #
            # caveat: Metzg. and Metzg.(asse) collisions
            for offset, frag in enumerate(line_fragments):
                offset = int(offset)

                frag_identified = False

                if islastname(frag):
                    scored_line['lastnames'].setdefault(frag, offset)
                    frag_identified = True
                    total_found += 1

                # allows multiple of same
                # useful for J. J. Rousseau
                if isgivenname(frag):
                    scored_line['givennames'].setdefault(frag + '-%s' % offset, offset)
                    frag_identified = True
                    total_found += 1

                if isoccupation(frag) and not isstreet(frag):
                    scored_line['occupations'].setdefault(frag, offset)
                    frag_identified = True
                    total_found += 1

                # prioritize over ambiguity Metzg.
                if (isstreet(frag) and not
                        (frag in scored_line['occupations'] and
                        len(scored_line['occupations']) < 1)):
                    scored_line['streets'].setdefault(frag, offset)
                    frag_identified = True
                    total_found += 1

                if ishousenumber(frag):
                    scored_line['housenumber'].setdefault(frag, offset)
                    frag_identified = True
                    total_found += 1

                if istitle(frag):
                    scored_line['title'].setdefault(frag, offset)
                    frag_identified = True
                    total_found += 1

                # allows multiple of same ('d.')
                if isjoinword(frag):
                    scored_line['joinword'].setdefault(frag + '-%s' % offset, offset)
                    frag_identified = True
                    total_found += 1

                if isaffix(frag):
                    scored_line['affix'].setdefault(frag, offset)
                    frag_identified = True
                    total_found += 1

                # never seen this frag before, store
                # it for human review
                #
                # note: these can be consumed using
                # ACCEPT_MAX_UNKNOWN_FRAGS > 0
                if not frag_identified:
                    scored_line['unknown'].setdefault(frag, offset)
                    unknown_fragments.setdefault(frag, 0)
                    unknown_fragments[frag] += 1

                # first frag is usually lastname
                # record them so we can create a ranking
                # for human review
                #
                # TODO(random-ao): thise is much less
                # useful today, compared to unknown-frags
                if offset == 0 and not frag_identified:
                    missing_lastnames.setdefault(frag, 0)
                    missing_lastnames[frag] += 1

                # second frag is often givenname
                # record them so we can create a ranking
                # for human review
                #
                # TODO(random-ao): thise is much less
                # useful today, compared to unknown-frags
                if offset == 1 and not frag_identified:
                    missing_givennames.setdefault(frag, 0)
                    missing_givennames[frag] += 1

            # verbose way of keeping overall stats
            if (len(scored_line['lastnames']) > 0 and
                len(scored_line['givennames']) > 0 and
                len(scored_line['streets']) > 0 and
                len(scored_line['occupations']) > 0):
                known_good += 1
            else:
                known_bad += 1

            # if lastnames are also givennames (Ernst) or
            # occupations (Müller), we prioritize
            if len(scored_line['lastnames']) > 0:
                new_lnames = {}

                # we have 0 or >1 givennames,
                # move detected givennames which are
                # also firstnames to firstnames only
                for lname in scored_line['lastnames']:

                    # if frag is also in occupations,
                    # remove it from lastnames;
                    # this is too rough for Mrs Müller
                    # who happens to be a Müller by
                    # profession
                    # TODO(random-ao): revisit if needed
                    if lname in scored_line['occupations']:
                        total_found -= 1
                        continue

                    # we only have 1 lastname and
                    # 1 firstname, remove firstname
                    if (gnisln(lname, scored_line['givennames']) and
                        len(scored_line['givennames']) == 1 and
                        len(scored_line['lastnames']) == 1):
                        scored_line['givennames'] = {}
                        new_lnames.setdefault(lname, scored_line['lastnames'][lname])
                        total_found -= 1

                    # check for lastnames in givennames
                    elif not gnisln(lname, scored_line['givennames']):
                        new_lnames.setdefault(lname, scored_line['lastnames'][lname])
                    else:
                        total_found -= 1


                if len(new_lnames) > 0:
                    scored_line['lastnames'] = new_lnames


            # mint new line if:
            # 1. we've matched all fragments, or
            # 2. we accept some unknown fragments
            if (total_fragments == total_found or 
                    (len(scored_line['unknown']) > 0 and
                    ACCEPT_MAX_UNKNOWN_FRAGS > 0)):

                ret, score = joiner(scored_line, total_found)

                mint_line = '%s  #%s#s=%s' % (ret, line.split('#')[1].rstrip(), score)

                # diff the newly minted line against
                # original, allows gating of greed
                match_ratio = SequenceMatcher(lambda x: x in ',', line.rstrip(), mint_line).ratio()

                # TODO(random-ao): match_ratio to output?
                # would allow tuning at pres.layer
                mint_line += '\n'

                if match_ratio < SEQUENCE_MATCH_THRESHOLD or score == 0:
                    if DEBUG_TO_STDOUT:
                        print('==========abandoned==========')
                        print('original line: %s' % line.strip())
                        print('resulting line: %s' % mint_line.strip())
                        print('similarity too low: %s' % (match_ratio, SEQUENCE_MATCH_THRESHOLD))
                        print('matched segments: %s\n\n' % scored_line)
                        print('===============================')

                    new_line_buffer.append(line)
                else:
                    seq_ok += 1
                    new_line_buffer.append(mint_line)
            else:
                # recycle line
                new_line_buffer.append(line)

                if DEBUG_TO_STDOUT:
                    print('==========unmatched==========')
                    print('original line: %s' % line.strip())
                    print('matched segments: %s\n\n' % scored_line)
                    print('total fragmentss vs total found: %s:%s' % (total_fragments, total_found))
                    print('unknown fragments: %s' % scored_line['unknown'])
                    print('===============================')

        # if seq ok, write file to proofread/stage
        # TODO(random-ao): remove staging once
        # we're confident enough
        path_segs = vol.split('/')
        fn = ('/'.join(path_segs[:-1]) + '/stage/' + '/'.join(path_segs[-1:]))
        with open(fn + '.tmp', 'w') as out:
            for line in new_line_buffer: out.write(line)
        os.rename(fn + '.tmp', fn)


    # write out missing segments
    # 1. lastnames to unknown-lastnames.csv
    # 2. givennames to unknown-givennames.csv
    # 3. everthing to unknown-fragments.csv
    if WRITE_UNKNOWN_FRAGMENT_LIST:
        missing_lastnames_list = sorted(missing_lastnames.items(), key=lambda x: x[1])
        with open('unknown-lastnames.csv', 'w', newline='') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            for item in missing_lastnames_list:
                wr.writerow([item[0], item[1]])

        missing_givennames_list = sorted(missing_givennames.items(), key=lambda x: x[1])
        with open('unknown-givennames.csv', 'w', newline='') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            for item in missing_givennames_list:
                wr.writerow([item[0], item[1]])

        unknown_fragments_list = sorted(unknown_fragments.items(), key=lambda x: x[1])
        with open('unknown-fragments.csv', 'w', newline='') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            for item in unknown_fragments_list:
                wr.writerow([item[0], item[1]])

    print('Results: %s (total), %s (good), %s (bad), %s (seq ok)' % (total_lines, known_good, known_bad, seq_ok))

if __name__ == '__main__':
    inspect()
