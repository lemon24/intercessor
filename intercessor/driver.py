from __future__ import print_function

from ._compat import input
from .watch import Alarm
from .notebook import parse_notebook


class Driver(object):

    def __init__(self, notebook_path, completer):
        self.notebook_path = notebook_path
        self.completer = completer
        self.name = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __call__(self, do):
        name = None
        while name is None:
            try:
                name = input('>>> at {!r}; run: '.format(self.name)).strip()
                break
            except EOFError:
                print('>>> eof, ignoring for now')
            except Alarm:
                print('>>> file changed, should reload notebook')

        with open(self.notebook_path) as f:
            notebook_text = f.read()
        cells = parse_notebook(notebook_text)

        self.completer.words = list(cells)

        if not name:
            name = self.name
        else:
            self.name = name

        do((name, cells[name]))

        return False


