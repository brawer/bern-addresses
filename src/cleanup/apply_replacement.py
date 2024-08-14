import os
import re


FIXES = [
    (r'Igfr\.', 'Jgfr.'),
    # << Bärag >> --> «Bärag»
    (r'<<\s*', '«'),
    (r'<«\s*', '«'),
    (r'\s*>>', '»'),
    (r'\s*»>', '»'),

    # Willy A,, Vers.-Angestellter --> Willy A., Vers.-Angestellter
    #(r' ([A-Z]),, ', ' \g<1>., '),

    (r'[ ]?\. \.,? ', '., '),

    (r',,(\w+)"', '„\g<1>“'),
    (r'\.„', '. „'),
    (r' 0\.', ' O.'),
    (r'Gertrud\.', 'Gertrud,'),
    (r'Hans\.', 'Hans,'),
    (r'Hedwig\.', 'Hedwig,'),
    (r'Ida\.', 'Ida,'),
    (r'Jakob\.', 'Jakob,'),
    (r'Robert\.', 'Robert,'),
    (r'Rudolf\.', 'Rudolf,'),
    (r'Ernst\.', 'Ernst,'),
    (r'Frieda\.', 'Frieda,'),
    (r'Fritz\.', 'Fritz,'),
    (r'Emma\.', 'Emma,'),
    (r'Arnold\.', 'Arnold,'),
    (r'Alfred\.', 'Alfred,'),
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
    # re-fix firstnames plus some (see above)
    (r'Alfred\.,', r'Alfred,'),
    (r'Anna\.,', r'Anna,'),
    (r'Arnold\.,', r'Arnold,'),
    (r'Bernhard\.,', r'Bernhard,'),
    (r'Ernst\.,', r'Ernst,'),
    (r'Fritz\.,', r'Fritz,'),
    (r'Gertrud\.,', r'Gertrud,'),
    (r'Hans\.,', r'Hans,'),
    (r'Jakob\.,', r'Jakob,'),
    (r'Lenhard\.,', r'Lenhard,'),
    (r'Margaritha\.,', r'Margaritha,'),
    (r'Marie\.,', r'Marie,'),
    (r'Martha\.,', r'Martha,'),
    (r'Olga\.,', r'Olga,'),
    (r'Otto\.,', r'Otto,'),
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
]


def apply_replacements():
    dirpath = os.path.join(os.path.dirname(__file__), '..', '..', 'proofread')
    print(dirpath)
    for filename in sorted(os.listdir(dirpath)):
        if not filename.endswith('.txt'):
            continue
        path = os.path.join(dirpath, filename)
        with open(path, 'r') as f:
            content = f.read()
        for (fro, to) in FIXES:
            content = re.sub(fro, to, content)
        with open(path, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    apply_replacements()
