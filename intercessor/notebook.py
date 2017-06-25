from __future__ import print_function

import re
from collections import OrderedDict
import traceback


# We need to accomodate this kind of workflow:
# https://ipython.org/ipython-doc/1/interactive/notebook.html#keyboard-shortcuts


def parse_notebook(text):
    parts = re.split('\s*\n#: +(.*)\n\s*', '\n'+text+'\n')
    assert parts[0].strip() == ''
    if len(parts) % 2 == 1:
        parts.append('')
    parts = iter(parts)
    next(parts)
    parts = zip(parts, parts)
    return OrderedDict(parts)


def make_target():
    locals = {}
    def target(arg):
        name, text = arg
        print('>>> running {!r}'.format(name))
        print('\n'.join('... ' + l for l in text.splitlines()))
        try:
            exec(text, {}, locals)
        except Exception:
            traceback.print_exc()
    return target


