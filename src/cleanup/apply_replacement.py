import os
import re

# TODO(random-ao): cleanup, also split into pre-post
FIXES = [
    # << Bärag >> --> «Bärag»
    (r"<<[ ]*", "«"),
    (r"<«[ ]*", "«"),
    (r"[ ]*>>", "»"),
    (r"[ ]*»>", "»"),
    (r"<([\w\s\.\,]*)>", "«\g<1>»"),
    (r"<([\w\s\.\,]*)»", "«\g<1>»"),
    (r"«([\w\s\.\,]*)>", "«\g<1>»"),
    (r"«\s?(\w*)\s?»", "«\g<1>»"),
    (r"[»]{2,}", "»"),
    (r"[«]{2,}", "«"),
    # »Merkur«
    (r"»([\w]*)«", "«\g<1>»"),
    # «zum Lütty«
    (r"«([\w]*)«", "«\g<1>»"),
    # »Agrippina"
    (r'»([\w\s\.]*)"', "«\g<1>»"),
    # * St. Galler Broderie»
    (r"\*([\w\s\.]*)»", "«\g<1>»"),
    # trim
    (r"[ ]+»", "»"),
    (r"«[ ]+", "«"),
    # '«Diskus,'
    (r"«(\w*),(?!.*»)", "«\g<1>»,"),
    # '«Spada»Nahrungsmittel'
    (r"»([A-Za-z])", "» \g<1>"),
    # ,,La Pergola"
    (r',,([ \w]*)"', "„\g<1>“"),
    # ,PRAXIS"
    (r',([\w]+)"', "„\g<1>“"),
    # des„Intelligenzblatt“ and 12„Jolimont“
    (r"(?<![\s(])([A-Za-z0-9]*)„", "\g<1> „"),
    # Alex 0.
    (r" 0\.", " O."),
    # Ernsi
    ("Ernsi", "Ernst"),
    # Herm
    ("Herrn\.", "Herm."),
    # Jgfr
    (r"Igfr\.", "Jgfr."),
    # Job
    ("Job\.", "Joh."),
    # Nealsch > Realsch
    (r"Nealsch", r"Realsch"),
    # Anstait > Anstalt
    (r"Anstait", r"Anstalt"),
    # «Genferhaus,»
    (r"«Genferhaus,»", r"«Genferhaus»"),
    # KarlSchenk-Haus
    (r"KarlSchenk-Haus", r"Karl-Schenk-Haus"),
    # Suvahaus>
    (r"Suvahaus>", r"«Suvahaus»"),
    # La Genevoise >
    (r"La Genevoise >", r"«La Genevoise»"),
    # Gehülf
    ("(g|G)ehiilf", "\g<1>ehülf"),
    # phone number indicator
    (r"£(\d\d+)", "↯\g<1>"),
    # Schiosser
    (r"Schiosser", r"Schlosser"),
    # Pau!
    (r"Pau!", r"Paul"),
    # Längegasse
    (r"Längegasse", r"Länggasse"),
    # Längsgasse
    (r"Längsgasse", r"Länggasse"),
    # Schauplag/gasse
    (r"Schauplagg", r"Schauplatzg"),
    # Meggergasse/Meßgerg
    (r"Megg", r"Metzg"),
    (r"Mgg", r"Mtzg"),
    (r"Meßg", r"Metzg"),
    # Elife
    (r"Elife", r"Elise"),
    # Nud.
    (r"Nud\.", r"Rud."),
    # Schriftseger
    (r"Schriftseger", r"Schriftsetzer"),
    # Nentiere
    (r"Nentier", r"Rentier"),
    (r"[ ]?\. \.,? ", "., "),
    (r"\.„", ". „"),
    (r",, ", r"., "),
    (r"\.\., ", r"., "),
]


def fix_givennames(content):
    gnpath = os.path.join(os.path.dirname(__file__), "frequent_given_names_nonabbr.txt")
    # TODO(random-ao): fold frequent_given_names{,_nonabbr_ambig}.txt

    givennames = {name.rstrip() for name in open(gnpath, "r")}

    for gn in givennames:
        # don't check < 3 char names
        if len(gn) <= 2:
            continue

        # TODO(random-ao): double replace here is expensive
        content = content.replace("%s." % gn, "%s," % gn)
        content = content.replace("%s,," % gn, "%s," % gn)
    return content


def fix_occupations(content):
    path = os.path.join(os.path.dirname(__file__), "..", "occupations.csv")

    occupations = {occ.split(",")[0] for occ in open(path, "r")}

    for occ in occupations:
        # TODO(random-ao): double replace here is expensive
        content = content.replace("%s." % occ, "%s," % occ)
        content = content.replace("%s,," % occ, "%s," % occ)
    return content


def apply_replacements():
    dirpath = os.path.join(os.path.dirname(__file__), "..", "..", "proofread")
    for filename in sorted(os.listdir(dirpath)):
        if not filename.endswith(".txt"):
            continue

        env_vl = os.environ.get("PROCESS_VOLUMES", False)
        if env_vl:
            vl = env_vl.split(",")
            if filename.split("/")[-1][:-4] not in vl:
                continue

        print("Processing replacements in %s" % filename)

        path = os.path.join(dirpath, filename)
        with open(path, "r") as f:
            content = f.read()

        # regex replacements
        for fro, to in FIXES:
            content = re.sub(fro, to, content)

        # string replacements
        content = fix_givennames(content)
        content = fix_occupations(content)

        with open(path, "w") as f:
            f.write(content)


if __name__ == "__main__":
    apply_replacements()
