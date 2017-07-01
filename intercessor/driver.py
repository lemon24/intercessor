from __future__ import print_function
import traceback

from ._compat import input
from .watch import WatchAlarm
from .notebook import parse_notebook


class Driver(object):

    def __init__(self, notebook_path, kernel, completer, watch):
        self.notebook_path = notebook_path
        self.kernel = kernel
        self.completer = completer
        self.watch = watch
        self.name = None
        self.cells = None

    def __call__(self):
        while True:
            try:
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
                reload = False
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
                        reload = True
                        break

                if reload:
                    continue

                if not name:
                    name = self.name
                else:
                    self.name = name

                self.kernel(name, self.cells[name])    # TODO: handle KeyError
            except KeyboardInterrupt:
                if confirm_terminate():
                    break


def make_target():
    locals = {}
    def target(name, text):
        print('>>> running {!r}'.format(name))
        print('\n'.join('... ' + l for l in text.splitlines()))
        try:
            exec(text, {}, locals)
        except Exception:
            traceback.print_exc()
    return target


def confirm_terminate():
    try:
        rv = input("terminate? [y/N]: ")
        return rv.strip().lower() == 'y'
    except EOFError:
        return False
    except KeyboardInterrupt:
        return True

