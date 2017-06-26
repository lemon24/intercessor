from __future__ import print_function

from ._compat import input
from .watch import WatchAlarm
from .notebook import parse_notebook


class Driver(object):

    def __init__(self, notebook_path, completer, watch):
        self.notebook_path = notebook_path
        self.completer = completer
        self.watch = watch
        self.name = None

    def __enter__(self):
        self.watch.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.watch.stop()
        return False

    def __call__(self, do):
        name = None
        while name is None:
            try:
                with self.watch.alarm():
                    name = input('>>> at {!r}; run: '.format(self.name)).strip()
                break
            except EOFError:
                print('>>> eof, ignoring for now')
            except WatchAlarm:
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


