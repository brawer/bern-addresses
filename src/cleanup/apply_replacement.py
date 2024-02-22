import os
import re

FIXES = [
    (r'Emma\.', 'Emma,'),
    #(r'Arnold\.', 'Arnold,'),
    #(r'Alfred\.', 'Alfred,'),
    #('(g|G)ehiilf', '\g<1>ehülf'),
    #('Herrn\.', 'Herm.'),
    #('Job\.', 'Joh.'),
    #(r'£(\d\d+)', '↯\g<1>'),
    #(r'gasse(\d+)', r'gasse \g<1>'),
    #(r'Kirclienfeld|Kirchen-\sIfeld', r'Kirchenfeld'),
    #(r'\\Vildhain'  , r'Wildhain'),
    #(r'^\d+\s+(.+)$'
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
