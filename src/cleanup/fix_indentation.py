# SPDX-FileCopyrightText: 2023 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT


import io
import os


# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )


def fix_indentation():
    path = os.path.join(os.path.dirname(__file__), 'frequent_given_names.txt')
    givennames = {name.strip() for name in open(path, 'r')}
    for vol in list_volumes():
        with open(vol + '.tmp', 'w') as out:
            for line in open(vol, 'r'):
                line = line.strip()
                if not line:
                    continue
                # TODO(random-ao): is whitespace split
                # really useful? revisit, save cycles
                if (line.split(',')[0] in givennames
                    or line.split()[0] in givennames):
                        out.write('- ' + line + '\n')
                else:
                    out.write(line + '\n')
        os.rename(vol + '.tmp', vol)


if __name__ == "__main__":
    fix_indentation()
