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
  print("Loaded %s lines to blackhole." % len(lut))

  whitelist = [
    '1861-04-15.txt',
    '1873-03-31.txt',
    '1875-05-31.txt',
    '1877-03-31.txt',
    '1879-06-30.txt',
    '1881-09-30.txt',
    '1882-12-15.txt',
    '1885-12-15.txt',
    '1888-08-01.txt',
    '1891-05-31.txt',
    '1893-05-31.txt',
    '1894-06-15.txt',
    '1895-05-31.txt',
    '1896-11-15.txt',
    '1897-07-15.txt',
    '1898-12-01.txt',
    '1900-02-15.txt',
    '1901-08-20.txt',
    '1902-10-04.txt',
    '1903-11-02.txt',
    '1904-11-30.txt',
    '1905-11-15.txt',
    '1906-11-25.txt',
    '1907-11-15.txt',
    '1908-11-10.txt',
    '1909-10-25.txt',
    '1910-10-22.txt',
    '1911-10-31.txt',
    '1912-11-15.txt',
    '1913-11-08.txt',
    '1915-06-10.txt',
    '1916-11-30.txt',
    '1918-01-31.txt',
    '1918-12-15.txt',
    '1919-12-15.txt',
    '1920-12-15.txt',
    '1921-12-15.txt',
    '1922-12-15.txt',
    '1923-12-15.txt',
    '1924-12-15.txt',
    '1925-12-15.txt',
    '1926-12-15.txt',
    '1927-12-15.txt',
    '1928-12-15.txt',
    '1929-12-15.txt',
    '1930-12-15.txt',
    '1931-12-15.txt',
    '1932-12-15.txt',
    '1933-12-15.txt',
    '1934-12-15.txt',
    '1935-12-15.txt',
    '1936-12-15.txt',
    '1937-12-05.txt',
    '1938-12-15.txt',
    '1939-12-31.txt',
    '1940-12-15.txt',
    '1941-12-15.txt',
    '1942-12-15.txt',
    '1943-12-15.txt',
    '1944-12-15.txt',
  ]
  for vol in list_volumes():
    # TODO(otz): remove gate
    if os.path.split(vol)[1] not in whitelist:
      continue
    print("Blackholing lines in %s" % vol)

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
