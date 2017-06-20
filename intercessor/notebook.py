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


def make_driver(notebook_path, completer):
    name = old_name = None

    def driver(do):
        nonlocal name
        nonlocal old_name

        name = input('>>> at {!r}; run: '.format(old_name)).strip()
        # TODO: handle EOF

        with open(notebook_path) as f:
            notebook_text = f.read()
        cells = parse_notebook(notebook_text)

        completer.words = list(cells)

        if not name.strip():
            name = old_name
        else:
            old_name = name

        do((name, cells[name]))

        return False

    return driver

