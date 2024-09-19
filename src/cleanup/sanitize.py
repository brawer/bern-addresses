import os
import re

FIXES = [
    # '[\w]=  #'
    (r'(\w+)=  #', r'\g<1> @@@GLUE@@@  #'),
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
