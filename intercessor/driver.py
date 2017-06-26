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
        self.cells = None

    def __enter__(self):
        self.watch.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.watch.stop()
        return False

    def __call__(self, do):
        reload = False
        if self.cells is None:
            reload = True
        elif self.watch.changed:
            print(">>> file changed during cell run")
            reload = True

        if reload:
            print(">>> reloading notebook")
            with open(self.notebook_path) as f:
                notebook_text = f.read()
            self.cells  = parse_notebook(notebook_text)
            self.completer.words = list(self.cells)

        name = None
        while name is None:
            try:
                with self.watch.alarm():
                    name = input('>>> at {!r}; run: '.format(self.name)).strip()
                break
            except EOFError:
                print('>>> eof, ignoring for now')
            except WatchAlarm:
                print('>>> file changed during input()')
                self.cells = None
                return False

        if not name:
            name = self.name
        else:
            self.name = name

        do((name, self.cells[name]))    # TODO: handle KeyError

        return False


