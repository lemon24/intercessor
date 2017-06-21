import sys

PY2 = sys.version_info[0] == 2

if PY2:
    input = raw_input
else:
    input = input

