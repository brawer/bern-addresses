import os
import re

FIXES = [
    # '[\w]=  #'
    (r'(\w+)=  #', r'\g<1> @@@GLUE@@@  #'),
    # Schauplag/gasse
    (r'Schauplagg', r'Schauplatzg'),
    # Meggergasse/Meßgerg
    (r'Megg', r'Metzg'),
    (r'Mgg', r'Mtzg'),
    (r'Meßg', r'Metzg'),
    # fix .*gaffe > gasse
    (r'gaffe', r'gasse'),
    # fix Framg*
    (r'Framg', r'Kramg'),
    # fix Narbg
    (r'Narbg', r'Aarbg'),
    # gasse12 > gasse 12
    (r'gasse(\d+)', r'gasse \g<1>'),
    # Kirchenfeld
    (r'Kirclienfeld|Kirchen-\sIfeld', r'Kirchenfeld'),
    # Wildhain
    (r'\\Vildhain', r'Wildhain'),
    # Junterng
    (r'Junterng', r'Junkerng'),
    # gåßlein
    (r'gåßlein', r'gäßlein'),
    # various Z fixes
    (r'3wicky', r'Zwicky'),
    (r'3ybach', r'Zybach'),
    (r'3yffet', r'Zysset'),
    (r'3weili', r'Zweili'),
    (r'Burlinden', r'Zurlinden'),
    (r'3ürni', r'Zürni'),
    (r'Büttel', r'Züttel'),
    (r'3wahlen', r'Zwahlen'),
    (r'3weyacker', r'Zweyacker'),
    (r'3yro', r'Zyro'),
    # Beughausg > Zeughausg
    (r'Beughausg', r'Zeughausg'),
    # Narbergergasse > Aarbergergasse
    (r'Narbergergasse', r'Aarbergergasse'),
    # Junferng > Junkerng
    (r'Junferng', r'Junkerng'),
    # Waisenhausplag, Kornhausplag, Bahnhofplag, Bärenplag,..
    (r'plag', r'platz'),
    (r'play', r'platz'),
    (r'Waisenhausplat ', r'Waisenhausplatz '),
    # Schriftseger > Schriftsetzer
    (r'Schriftseger', r'Schriftsetzer'),
    # remove phone numbers
    (r'\[ ?\d+\.?\:?-? ?\d+\.?-? *\d*\]?\)?', ''),
]

def sanitize():

    dirpath = os.path.join(os.path.dirname(__file__), '..', '..', 'proofread')
    for filename in sorted(os.listdir(dirpath)):
        if not filename.endswith('.txt'):
            continue

        env_vl = os.environ.get('PROCESS_VOLUMES', False)
        if env_vl:
            vl = env_vl.split(',')
            if filename.split('/')[-1][:-4] not in vl:
                continue

        print('Sanitizing %s' % filename)

        path = os.path.join(dirpath, filename)
        with open(path, 'r') as f:
            content = f.read()

        # regex replacements
        for (fro, to) in FIXES:
            content = re.sub(fro, to, content)

        with open(path, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    sanitize()
