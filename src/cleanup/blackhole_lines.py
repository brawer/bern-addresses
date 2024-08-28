import os

# Returns the file paths to all address book volumes.
def list_volumes():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "proofread")
    path = os.path.normpath(path)
    return sorted(
        [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".txt")]
    )

def strip_lines():

  lut = {}
  lut_raw_fn = os.path.join(os.path.dirname(__file__), "..", "blackhole-lines.txt")
  with open(lut_raw_fn) as fp:
    for line in fp:
       lut[line] = 0
  print('Loaded %s lines to blackhole.' % len(lut))

  for vol in list_volumes():
    print('Processing blackholes in %s' % vol)

    num_blackholes = 0

    with open(vol + '.tmp', 'w') as out:
      for line in open(vol, 'r'):

        if line in lut:
          num_blackholes += 1
          continue
        
        out.write(line)
      os.rename(vol + '.tmp', vol)
      print("%s lines removed" % num_blackholes)


if __name__ == "__main__":
    strip_lines()
