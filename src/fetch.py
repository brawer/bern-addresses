# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT
#
# Fetch address books of Bern (1860-1945) from www.e-rara.ch,
# and auxiliary data (such as famiily names) from Wikidata.

from collections import namedtuple
import csv
import gzip
import http
import io
import requests
import os
import re
import sqlite3
import xml.etree.ElementTree as etree
import urllib


Chapter = namedtuple('Chapter', ['id', 'title', 'date', 'year', 'volume', 'pages'])
Page = namedtuple('Page', ['id', 'label'])


ALTO_SPACE = '{http://www.loc.gov/standards/alto/ns-v3#}SP'
ALTO_STRING = '{http://www.loc.gov/standards/alto/ns-v3#}String'
ALTO_TEXTLINE = '{http://www.loc.gov/standards/alto/ns-v3#}TextLine'


def is_uppercase(c):
    return c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜÉÈ'

def is_lowercase(c):
    return c in 'abcdefghijklmnopqrstuvwxyzäöüéè'


class Extractor(object):
    def __init__(self, cachedir):
        self.cachedir = cachedir
        self.ads_denylist = self.read_ads_denylist()
        self.families = self.read_families()
        self.wikidata_family_names = self.read_wikidata_family_names()

    def run(self):
        if not os.path.exists(self.cachedir):
            os.mkdir(self.cachedir)
        #self.process_proofread()
        for chapter in self.find_chapters():
            if chapter.date[:4] in ['1944', '1861']:
                continue
            with open(f'proofread/{chapter.date}.txt', 'w') as out:
                for page in chapter.pages:
                    self.process_page(chapter, page, out)

    def process_page(self, chapter, page, out):
        et = etree.fromstring(self.fetch_page_xml(page.id))
        out.write(f'# Date: {chapter.date} Page: {page.id}/{page.label}\n')
        lines = []
        cur_line = ''
        for line in et.findall(f'.//{ALTO_TEXTLINE}'):
            tokens = []
            for e in line:
                if e.tag == ALTO_STRING:
                    tokens.append(e.attrib['CONTENT'])
                elif e.tag == ALTO_SPACE:
                    tokens.append(' ')
            this_line = ''.join(tokens)
            this_line = this_line.replace('[', ' [')
            if this_line.startswith('■—') or this_line.startswith('*-'):
                this_line = this_line[1:]
            if this_line[0] in '-–—':
                this_line = '– ' + this_line[1:]
            this_line = ' '.join(this_line.split())
            if cur_line.endswith('-'):
                if is_uppercase(this_line[0]):
                    cur_line = cur_line + this_line
                else:
                    cur_line = cur_line[:-1] + this_line
            elif cur_line.endswith(',') or cur_line.endswith(' und') or this_line[0] == '[':
                cur_line = cur_line + ' ' + this_line
            elif is_lowercase(this_line[0]):
                cur_line = cur_line + this_line
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = this_line
        if cur_line:
            lines.append(cur_line)
        if len(lines) > 10 and all(len(lines[i].split()) == 1 for i in (0,1,2)):
            lines = lines[3:]
        for line in lines:
            out.write(line + '\n')

    def find_chapters(self):
        chapters = []
        path = os.path.join(os.path.dirname(__file__), 'chapters.csv')
        with open(path) as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
            csvfile.seek(0)
            for row in csv.DictReader(csvfile, dialect=dialect):
                chapter_id = int(row['ChapterID'])
                volume_id = int(row['VolumeID'])
                date = row['Date']
                if len(date) == 4:
                    date = '%04d-12-15' % (int(date) - 1)
                pages = self.find_chapter_pages(volume_id, chapter_id)
                chapter = Chapter(id=chapter_id,
                                  title=row['ChapterTitle'],
                                  date=date,
                                  year=row['Year'],
                                  volume=volume_id,
                                  pages=pages)
                chapters.append(chapter)
        return chapters

    def find_chapter_pages(self, volume_id, chapter_id):
        et = etree.fromstring(self.fetch_volume_mets(volume_id))
        page_labels = {}
        for smap in et.iter('{http://www.loc.gov/METS/}structMap'):
            if smap.attrib['TYPE'] == 'PHYSICAL':
                for div in smap.iter('{http://www.loc.gov/METS/}div'):
                    if div.attrib['TYPE'] == 'page':
                        page_id = int(div.attrib['ID'].removeprefix('phys'))
                        if label := div.attrib.get('ORDERLABEL'):
                            page_labels[page_id] = label
        pages = []
        for link in et.iter('{http://www.loc.gov/METS/}smLink'):
            link_from  = link.attrib['{http://www.w3.org/1999/xlink}from']
            link_from_id = int(link_from.removeprefix("log"))
            if link_from_id == chapter_id:
                link_to = link.attrib['{http://www.w3.org/1999/xlink}to']
                page_id = int(link_to.removeprefix('phys'))
                if page_id not in self.ads_denylist:
                    page = Page(id=page_id, label=page_labels.get(page_id))
                    pages.append(page)

        # If the first page has no number, synthesize it: '[123]'.
        if not pages[0].label:
            pages[0] = Page(id=pages[0].id,
                            label = f'[%d]' % (int(pages[1].label) - 1))

        return pages

    def fetch_volume_mets(self, volume):
        filepath = f"{self.cachedir}/mets-{volume}.xml"
        if not os.path.exists(filepath):
            req = requests.get(
                "https://www.e-rara.ch/oai?verb=GetRecord&metadataPrefix=mets" +
                f"&identifier={volume}")
            with open(filepath, 'wb') as f:
                f.write(req.content)
        with open(filepath, 'rb') as f:
            return f.read()

    def fetch_page_xml(self, page_id):
        filepath = f"{self.cachedir}/fulltext-{page_id}.xml"
        if not os.path.exists(filepath):
            req = requests.get(f'https://www.e-rara.ch/bes_1/download/fulltext/alto3/{page_id}')
            with open(filepath+'.tmp', 'w') as f:
                f.write(req.text)
            os.rename(filepath+'.tmp', filepath)  # atomic
        with open(filepath, 'r') as f:
            return f.read()

    def process_proofread(self):
        dirpath = os.path.join(os.path.dirname(__file__), '..', 'proofread')
        for date in sorted(os.listdir(dirpath)):
            path = os.path.join(dirpath, date)
            for line in open(path):
                if line[0] == '#':
                    pass
                elif line[0] == '—':
                    pass
                else:
                    name = self.get_family_name(line)
                    if name not in self.families:
                        wikidata_id = self.wikidata_family_names.get(name)
                        if wikidata_id and ';' not in name:
                            print('%s;%s' % (name, wikidata_id))

    def get_family_name(self, line):
        if line.startswith('v.'):
            name = 'von ' + line[2:].split()[0]
        elif line.startswith('de '):
            name = 'de ' + line[2:].split()[0]
        else:
            name = line.split()[0]
        return name.removesuffix(',')

    def read_ads_denylist(self):
        result = set()
        for line in open(os.path.join(os.path.dirname(__file__), 'ads.txt')):
            line = line.strip()
            if line and line[0] != '#':
                result.add(int(line))
        return result

    def read_families(self):
        result = {}
        filepath = os.path.join(os.path.dirname(__file__), 'families.txt')
        for line in open(filepath):
            line = line.strip()
            if line and line[0] != '#':
                name, wikidata_id = line.split(';')
                result[name] = wikidata_id
        return result

    def read_wikidata_family_names(self):
        result = {}
        filepath = os.path.join(self.cachedir, 'wikidata_family_names.csv.gz')
        with gzip.open(filepath, mode='rb') as bytestream:
            with io.TextIOWrapper(bytestream, encoding='utf-8') as stream:
                for row in csv.DictReader(stream):
                    name, id = row['Name'], row['WikidataID']
                    result[name] = id
        return result


def make_request(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "BernAddressBookBot/1.0")
    req.add_header("From", "sascha@brawer.ch")
    return req


def fetch_request(req):
    retry = 0
    while True:
        try:
            response = urllib.request.urlopen(req, timeout=30)
            return response.read()
        except http.client.IncompleteRead as err:
            retry += 1
            if retry >= 5:
                raise err
        except TimeoutError as err:
            retry += 1
            if retry >= 5:
                raise err


def fetch_wikidata_family_names(cachedir):
    if not os.path.exists(cachedir):
        os.mkdir(cachedir)
    path = os.path.join(cachedir, "wikidata_family_names.csv.gz")
    if os.path.exists(path):
        return
    url = 'https://names.toolforge.org/downloads/familynames.csv.gz'
    with open(path + '.tmp', 'wb') as out:
        req = make_request(url)
        out.write(fetch_request(req))
    os.rename(path+'.tmp', path)


if __name__ == '__main__':
    cachedir = "cache"
    fetch_wikidata_family_names(cachedir)
    ex = Extractor(cachedir)
    ex.run()
