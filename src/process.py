# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Process Bern address books (1861-1945), using data produced by fetch.py.

from collections import Counter, namedtuple
import csv
import inspect
import os
import re


Record = namedtuple('Record', [
    'Name', 'Surname', 'Date', 'Street', 'Housenumber', 'Postcode', 'City',
    'Phone', 'PageID', 'Page', 'Latitude', 'Longitude',
])


class Processor(object):
    def __init__(self, cachedir):
        self.families = self.read_families()
        self.firstnames = self.read_firstnames()
        self.given_name_abbreviations = self.read_given_name_abbreviations()
        self.accepted_affixes = { # accepted fragments in firstnames
          "Frau": True,
          "Frl": True,
          "Frl.": True,
          "Gebr.": True,
          "Gebrüder": True,
          "Jgfr.": True,
          "Schwest.": True,
          "Schwestern": True,
          "Wittwe": True,
          "Wwe.": True
        };
        self.read_addresses()
        self.unknown_families = Counter()
        self.max_family_name_wordcount = max(
            len(f.split()) for f in self.families.keys())
        self.num_input_records = 0
        self.good_familyname_count = 0
        self.bad_familyname_count = 0
        self.good_firstname_count = 0
        self.bad_firstname_count = 0
        self.unknown_given_names = Counter()
        self.bad_address_count = 0

    def read_families(self):
        result = {}
        filepath = os.path.join(os.path.dirname(__file__), 'families.txt')
        for line in open(filepath):
            line = line.strip()
            if line and line[0] != '#':
                name, wikidata_id = line.split(';')
                result[name.lower()] = (name, wikidata_id)
        return result

    def read_firstnames(self):
        result = {}
        filepath = os.path.join(os.path.dirname(__file__), 'givennames_wikidata.csv')
        for line in open(filepath):
            line = list(csv.reader([line.strip()]))
            key = line[0][0].lower()
            value = line[0][1]
            result[key.lower()] = (line[0][0], value)
        return result

    def read_given_name_abbreviations(self):
        abbrevs = set()
        filepath = os.path.join(os.path.dirname(__file__), 'given_name_abbreviations.csv')
        with open(filepath) as stream:
            for row in csv.DictReader(stream):
                abbrevs.add(row['Abbreviation'])
        return abbrevs

    def read_addresses(self):
        self.streets = set()
        self.addresses = {}
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'pure_adr_be.csv')
        for line in open(filepath, 'r'):
            c = line.split(';')
            street, housenumber, postcode_city, lng, lat = \
                c[4], c[5], c[8], c[-2], c[-1]
            postcode, city = postcode_city.split(' ', 1)
            if city != 'Bern':
                continue
            lat, lng = round(float(lat), 6), round(float(lng), 6)
            self.addresses[(street, housenumber)] = (street, housenumber, postcode, city, lat, lng)
            self.streets.add(street)

    def process_proofread(self):
        dirpath = os.path.join(os.path.dirname(__file__), '..', 'proofread')
        page_re = re.compile(
            r'^# Date: (\d{4}-\d\d-\d\d) Page: (\d+)/[\[]?([\d]+)[\]]?$')
        for filename in sorted(os.listdir(dirpath)):
            if not filename.endswith('.txt'):
                continue
            #if filename[:4] not in ('1944'):
            #    continue
            path = os.path.join(dirpath, filename)
            publication_date, page_id, page_label = None, None, None
            line_num = 0
            family = None
            for line in open(path):
                line_num += 1
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == '#':
                    if m := page_re.match(line):
                        publication_date, page_id, page_label = m.groups()
                        self.publication_date = publication_date
                        self.page_id = page_id
                        self.page_label = page_label
                        family = None
                        continue
                    else:
                        raise ValueError(
                            f'{path}:{line_num}: Unknown # directive: {line}')
                self.num_input_records += 1
                if line[0] in ('—', '–', '-'):
                    rest = line[1:].strip()
                else:
                    family, rest = self.split_family_name(line)

                firstname = None
                if family and rest:
                    firstname, rest = self.split_given_name(rest);

                phone, rest = self.split_phone(rest)
                address, rest = self.split_address(rest)
                if not address:
                    self.bad_address_count += 1
                if family and firstname and address:
                    (street, housenumber, postcode, city, lat, lng) = address
                    yield Record(
                        Name=firstname,
                        Surname=family,
                        Date=self.publication_date,
                        Street=street,
                        Housenumber=housenumber,
                        Postcode=postcode,
                        City=city,
                        Latitude=lat,
                        Longitude=lng,
                        Phone=(';'.join(phone) if phone else ''),
                        PageID=self.page_id,
                        Page=self.page_label)
                #print(family, phone, rest)

    def split_family_name(self, line):
        line = line.removeprefix(',')
        line = line.replace(' - ', '-')
        if line.startswith('v.'):
            line = 'von ' + line[3:].strip()
        frags = line.split(',')
        words = frags[0].split()
        for n in reversed(range(self.max_family_name_wordcount)):
            name_key = ' '.join(words[:n+1]).lower()
            if name := self.families.get(name_key):
                self.good_familyname_count += 1
                return (name[0], ','.join(frags[1:]))
        self.unknown_families[words[0]] += 1
        self.report_unknown_name(line)
        self.bad_familyname_count += 1
        return (None, ','.join(frags[1:]))

    def report_unknown_name(self, line):
        #print(inspect.stack()[1].function + ": " + line)
        #print(self.publication_date, line)
        pass

    def split_given_name(self, line):
        parts = line.split(',')
        firstname = parts[0].strip()
        firstname_frags = firstname.split(' ')
        all_frags_found = True
        for frag in firstname_frags:
            if frag in self.given_name_abbreviations:
                continue
            if self.firstnames.get(frag.lower()):
                continue
            if self.accepted_affixes.get(frag):
                continue
            all_frags_found = False
        if all_frags_found:
            self.good_firstname_count += 1
            return (firstname, ','.join(parts))
        self.unknown_given_names[firstname] += 1
        self.report_unknown_name(line)
        self.bad_firstname_count += 1
        return (None, line)

    def split_address(self, line):
        for suffix in ['Bümpliz', 'Riedbach', 'Oberbottigen', ', ']:
            line = line.removesuffix(suffix)
        frags = line.split(',')
        tokens = frags[-1].strip().split(' ')
        if len(tokens) < 2:
            return None, line
        street, housenumber = tokens[-2], tokens[-1]
        # FIXME: heavy chances of phone here
        if street and street[-1] == '.':
            for abbr, full in [('w.', 'weg'), ('str.', 'strasse')]:
                if street.endswith(abbr):
                    street = street.removesuffix(abbr) + full
                    break
        if addr := self.addresses.get((street, housenumber)):
            return addr, ' '.join(tokens[:-2]).removesuffix(',')
        return None, line

    def split_phone(self, line):
        year = int(self.publication_date[:4])
        phone = None
        if year >= 1900 and year <= 1917:
            if m := re.match(r'^(.+\d(\s?[a-f])?) (\d{2,4})$', line):
                line, _, phone = m.groups()
                phone = [phone]
        elif year >= 1941:
            if m := re.findall(r'\[((\d\s*){5})\]', line):
                phone = [normalize_phone(p[0], year) for p in m]
            line = re.sub(r'\s?\[.+?\]', '', line)
        return phone, line


def normalize_phone(phone, year):
     d = phone.replace(' ', '')
     if year >= 1944:
         return ' '.join((d[0], d[1:3], d[3:]))
     return ''


def read_wikidata_family_names():
        import gzip, io
        result = {}
        filepath = os.path.join('cache', 'wikidata_family_names.csv.gz')
        with gzip.open(filepath, mode='rb') as bytestream:
            with io.TextIOWrapper(bytestream, encoding='utf-8') as stream:
                for row in csv.DictReader(stream):
                    name, id = row['Name'], row['WikidataID']
                    result[name] = id
        return result


if __name__ == '__main__':
    # wd = read_wikidata_family_names()
    p = Processor(cachedir='cache')
    with open('bern-address-book.csv', 'w') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Name', 'Surname', 'Date', 'Street', 'Housenumber', 'Postcode', 'City', 'Latitude', 'Longitude', 'Phone', 'PageID', 'Page'])
        num_output_records = 0
        for rec in p.process_proofread():
            num_output_records += 1
            writer.writerow([rec.Name, rec.Surname, rec.Date,
                             rec.Street, rec.Housenumber, rec.Postcode,
                             rec.City, rec.Latitude, rec.Longitude,
                             rec.Phone,
                             rec.PageID, rec.Page])

    # write out unknown firstnames
    with open('givennames.unknown.csv', 'w') as fp:
        csvw = csv.writer(fp)
        csvw.writerows(p.unknown_given_names.most_common())

    total_familyname_count = p.good_familyname_count + p.bad_familyname_count
    good_percent = int(p.good_familyname_count * 100.0 / total_familyname_count + 0.5)
    total_firstname_count = p.good_firstname_count + p.bad_firstname_count
    good_firstname_percent = int(p.good_firstname_count * 100.0 / total_firstname_count + 0.5)
    print(f'records: input {p.num_input_records} -> output {num_output_records} = {int(num_output_records * 100.0 / p.num_input_records + 0.5)}%')
    print(f'family names: total {total_familyname_count}; known: {p.good_familyname_count} = {good_percent}%')
    print(f'firstnames: total {total_firstname_count}; known: {p.good_firstname_count} = {good_firstname_percent}%')

