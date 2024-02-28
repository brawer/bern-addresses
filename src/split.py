# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT


import io
import os
import re


GIVENNAMES = {
    line.strip()
    for line in open(os.path.join(os.path.dirname(__file__), 'givennames.txt'))
}


def split(vol):
    page_re = re.compile(r'^# Date: (\d{4}-\d{2}-\d{2}) Page: (\d+)/.*')
    # Date: 1860-02-01 Page: 29210065/62
    data, page, familyname = None, None, ''
    for line in open(vol):
        line = line.strip()
        if m := page_re.match(line):
            date, page = m.groups()
            continue
        p, pos = line.split('#', 1)
        p = [x.strip() for x in p.split(',')]
        fnam, rest = split_familyname(p[0])
        if fnam != '-':
            familyname = fnam
        maidenname, rest = split_maidenname(rest)
        #print(line)
        p = [rest] + p[1:] if rest else p[1:]
        title, p = split_title(p)
        address, p = split_address(p)
        givenname, p = split_givenname(p)
        print(f'fn="{familyname}" given="{givenname}" maiden="{maidenname}" title="{title}" addr="{address}" {p}')


def split_familyname(n):
    n = n.replace(' - ', '-')
    words = n.split()
    if words[0] in {'v.', 'V.', 'von', 'Von'}:
        if words[1].endswith('-v.'):  # "v. Wagner-v. Steiger A." -> ('von Wagner-von Steiger', 'A.')
            return ('von ' + words[1].replace('-v.', '-von') + ' ' + words[2], ' '.join(words[3:]))
        return ('von ' + words[1], ' '.join(words[2:]))
    else:
        return (words[0], ' '.join(words[1:]))


def split_givenname(p):
    if len(p) == 0:
        return ('', [])
    if all(n in GIVENNAMES for n in p[0].split()):
        return (p[0], p[1:])
    else:
        return ('', p)


def split_maidenname(n):
    if n.startswith('geb.') or n.startswith('gb.'):
        words = n.split()
        if len(words) >= 2:
            if words[1] in {'v.', 'V.', 'von', 'Von'} and len(words) >= 3:
                return ('von ' + words[2], ' '.join(words[3:]))
            else:
                return (words[1], ' '.join(words[2:]))
    return ('', n)


def split_title(p):
    if len(p) > 0 and p[0] in {'älter', 'jünger', 'Frau', 'Dr.', 'Frauen', 'Frln.', 'Frl.',
                               'Frau u. Tocht.', 'Gebr.', 'Jgfr.', 'Miß',
                               'Schwest.', 'Schwestern', 'Schwester', 'Sohn', 'Söhne',
                               'Töcht.', 'Töchter', 'Wtw.', 'Wwe.', 'Ww.', 'Vater', 'Wtw. und Sohn'}:
        return (p[0], p[1:])
    else:
        return ('', p)


def split_address(p):
    if len(p) == 0:
        return ('', [])
    last = p[-1].removesuffix('.')
    if m := re.match(r'(.+\d+) ([abcdefgh])', last):
        return (''.join(m.groups()), p[:-1])
    if last and last[-1] in '0123456789':
        return (last, p[:-1])
    return ('', p)


# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )


if __name__ == "__main__":
    for vol in list_volumes():
        if os.path.basename(vol).startswith('1860'):
            split(vol)

