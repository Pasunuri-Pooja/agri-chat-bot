# cgi.py shim for Python 3.13+
def parse_header(line):
    parts = line.split(";")
    key = parts[0].strip().lower()
    pdict = {}
    for item in parts[1:]:
        if "=" in item:
            k, v = item.strip().split("=", 1)
            pdict[k.lower()] = v.strip('"')
    return key, pdict
