from __future__ import print_function

import re
from collections import OrderedDict


def parse_notebook(text):
    parts = re.split('\s*\n#: +(.*)\n\s*', '\n'+text+'\n')
    assert parts[0].strip() == ''
    if len(parts) % 2 == 1:
        parts.append('')
    parts = iter(parts)
    next(parts)
    parts = zip(parts, parts)
    return OrderedDict(parts)

