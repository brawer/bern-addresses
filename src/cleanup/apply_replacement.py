import os
import re

# TODO(random-ao): cleanup, also split into pre-post
FIXES = [
    (r'Igfr\.', 'Jgfr.'),
    # << Bärag >> --> «Bärag»
    (r'<<[ ]*', '«'),
    (r'<«[ ]*', '«'),
    (r'[ ]*>>', '»'),
    (r'[ ]*»>', '»'),
    (r'<([\w\s\.\,]*)>', '«\g<1>»'),
    (r'<([\w\s\.\,]*)»', '«\g<1>»'),
    (r'«([\w\s\.\,]*)>', '«\g<1>»'),
    (r'«\s?(\w*)\s?»', '«\g<1>»'),
    (r'[»]{2,}', '»'),
    (r'[«]{2,}', '«'),
    # »Merkur«
    (r'»([\w]*)«', '«\g<1>»'),
    # «zum Lütty«
    (r'«([\w]*)«', '«\g<1>»'),
    # »Agrippina"
    (r'»([\w\s\.]*)"', '«\g<1>»'),
    # * St. Galler Broderie»
    (r'\*([\w\s\.]*)»', '«\g<1>»'),
    # trim
    (r'[ ]+»', '»'),
    (r'«[ ]+', '«'),
    # '«Diskus,'
    (r'«(\w*),(?!.*»)', '«\g<1>»,'),
    # '«Spada»Nahrungsmittel'
    (r'»([A-Za-z])', '» \g<1>'),

    # Willy A,, Vers.-Angestellter --> Willy A., Vers.-Angestellter
    #(r' ([A-Z]),, ', ' \g<1>., '),

    (r'[ ]?\. \.,? ', '., '),

    (r',,(\w+)"', '„\g<1>“'),
    (r'\.„', '. „'),
    (r' 0\.', ' O.'),
    ('(g|G)ehiilf', '\g<1>ehülf'),
    ('Herrn\.', 'Herm.'),
    ('Job\.', 'Joh.'),
    (r'£(\d\d+)', '↯\g<1>'),
    (r'gasse(\d+)', r'gasse \g<1>'),
    (r'Kirclienfeld|Kirchen-\sIfeld', r'Kirchenfeld'),
    (r'\\Vildhain'  , r'Wildhain'),
    (r'R\. B,,', r'R. B.,'),
    (r'K\. R,,', r'K. R.,'),
    (r',, ', r'., '),
    (r'\.\., ', r'., '),
    # fix Neuengaffe > Neuengasse
    (r'Neuengaffe', r'Neuengasse'),
    # replace known-good jobnames suffixed
    # by '.' w/',' suffix - hack, see below
    (r'Arzt\.', r'Arzt,'),
    (r'Ausläufer\.', r'Ausläufer,'),
    (r'Bäcker\.', r'Bäcker,'),
    (r'Bäcker-Konditor\.', r'Bäcker-Konditor,'),
    (r'Bahnarbeiter\.', r'Bahnarbeiter,'),
    (r'Bautechniker\.', r'Bautechniker,'),
    (r'Beamter\.', r'Beamter,'),
    (r'Bureaulistin\.', r'Bureaulistin,'),
    (r'Chemiker\.', r'Chemiker,'),
    (r'Coiffeuse\.', r'Coiffeuse,'),
    (r'Dachdecker\.', r'Dachdecker,'),
    (r'Förster\.', r'Förster,'),
    (r'Gymnasiallehrer\.', r'Gymnasiallehrer,'),
    (r'Handlanger\.', r'Handlanger,'),
    (r'Hotelexperte\.', r'Hotelexperte,'),
    (r'Kaufmann\.', r'Kaufmann,'),
    (r'Kommis\.', r'Kommis,'),
    (r'Konditor\.', r'Konditor,'),
    (r'Lithographiebesitzer\.', r'Lithographiebesitzer,'),
    (r'Maler\. ', r'Maler, '),
    (r'Mechaniker\.', r'Mechaniker,'),
    (r'Monteur\.', r'Monteur,'),
    (r'Oberbriefträger\.', r'Oberbriefträger,'),
    (r'Polizist\.', r'Polizist,'),
    (r'Schausteller\.', r'Schausteller,'),
    (r'Schiosser\.', r'Schiosser,'),
    (r'Schreiner\.', r'Schreiner,'),
    (r'Techniker\.', r'Techniker,'),
    (r'Telegraphist\.', r'Telegraphist,'),
    (r'Thierarzt\.', r'Thierarzt,'),
    (r'Verkäuferin\.', r'Verkäuferin,'),
    (r'Vertreter\.', r'Vertreter,'),
    (r'Walzenführer\.', r'Walzenführer,'),
    (r'Wegmeister\.', r'Wegmeister,'),
    (r'Zimmermann\.', r'Zimmermann,'),
    # and then replace ',,' ','
    # TODO(random-ao): nasty, re-impl
    (r'Arzt,,', r'Arzt,'),
    (r'Ausläufer,,', r'Ausläufer,'),
    (r'Bäcker,,', r'Bäcker,'),
    (r'Bäcker-Konditor,,', r'Bäcker-Konditor,'),
    (r'Bahnarbeiter,,', r'Bahnarbeiter,'),
    (r'Bautechniker,,', r'Bautechniker,'),
    (r'Beamter,,', r'Beamter,'),
    (r'Bureaulistin,,', r'Bureaulistin,'),
    (r'Chemiker,,', r'Chemiker,'),
    (r'Coiffeuse,,', r'Coiffeuse,'),
    (r'Dachdecker,,', r'Dachdecker,'),
    (r'Förster,,', r'Förster,'),
    (r'Gymnasiallehrer,,', r'Gymnasiallehrer,'),
    (r'Handlanger,,', r'Handlanger,'),
    (r'Hotelexperte,,', r'Hotelexperte,'),
    (r'Kaufmann,,', r'Kaufmann,'),
    (r'Kommis,,', r'Kommis,'),
    (r'Konditor,,', r'Konditor,'),
    (r'Lithographiebesitzer,,', r'Lithographiebesitzer,'),
    (r'Mechaniker,,', r'Mechaniker,'),
    (r'Monteur,,', r'Monteur,'),
    (r'Oberbriefträger,,', r'Oberbriefträger,'),
    (r'Polizist,,', r'Polizist,'),
    (r'Schausteller,,', r'Schausteller,'),
    (r'Schiosser,,', r'Schiosser,'),
    (r'Schreiner,,', r'Schreiner,'),
    (r'Techniker,,', r'Techniker,'),
    (r'Telegraphist,,', r'Telegraphist,'),
    (r'Thierarzt,,', r'Thierarzt,'),
    (r'Verkäuferin,,', r'Verkäuferin,'),
    (r'Vertreter,,', r'Vertreter,'),
    (r'Walzenführer,,', r'Walzenführer,'),
    (r'Wegmeister,,', r'Wegmeister,'),
    (r'Zimmermann,,', r'Zimmermann,'),
    # Nealsch > Realsch
    (r'Nealsch', r'Realsch'),
    # Anstait > Anstalt
    (r'Anstait', r'Anstalt'),
    # «Genferhaus,»
    (r'«Genferhaus,»', r'«Genferhaus»'),
    # KarlSchenk-Haus
    (r'KarlSchenk-Haus', r'Karl-Schenk-Haus'),
    # Suvahaus>
    (r'Suvahaus>', r'«Suvahaus»'),
    # La Genevoise >
    (r'La Genevoise >', r'«La Genevoise»'),
]

def fix_givennames(content):
    gnpath = os.path.join(os.path.dirname(__file__), 'frequent_given_names_nonabbr.txt')
    # TODO(random-ao): fold frequent_given_names{,_nonabbr_ambig}.txt

    givennames = {name.strip() for name in open(gnpath, 'r')}

    for gn in givennames:
        # don't check < 3 char names
        if len(gn) <= 2:
            continue

        # TODO(random-ao): double replace here is expensive
        content = content.replace("%s." % gn, "%s," % gn)
        content = content.replace("%s,," % gn, "%s," % gn)
    return content


def apply_replacements():

    dirpath = os.path.join(os.path.dirname(__file__), '..', '..', 'proofread')
    for filename in sorted(os.listdir(dirpath)):
        if not filename.endswith('.txt'):
            continue
        path = os.path.join(dirpath, filename)
        with open(path, 'r') as f:
            content = f.read()

        # regex replacements
        for (fro, to) in FIXES:
            content = re.sub(fro, to, content)

        # string replacements
        content = fix_givennames(content)

        with open(path, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    apply_replacements()
