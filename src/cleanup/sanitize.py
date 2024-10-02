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
