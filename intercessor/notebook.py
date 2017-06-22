from __future__ import print_function

import re
from collections import OrderedDict
import traceback

from ._compat import input
from .watch import Alarm


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


class Namespace(object):

    pass


def make_driver(notebook_path, completer):
    ns = Namespace()
    ns.name = ns.old_name = None

    def driver(do):
        name = None
        while not name:
            try:
                name = input('>>> at {!r}; run: '.format(ns.old_name)).strip()
                ns.name = name
                break
            except EOFError:
                print('>>> eof, ignoring for now')
            except Alarm:
                print('>>> file changed, should reload notebook')

        with open(notebook_path) as f:
            notebook_text = f.read()
        cells = parse_notebook(notebook_text)

        completer.words = list(cells)

        if not ns.name.strip():
            ns.name = ns.old_name
        else:
            ns.old_name = ns.name

        do((ns.name, cells[ns.name]))

        return False

    return driver

