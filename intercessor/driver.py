from __future__ import print_function
import traceback

from ._compat import input
from .watch import watch_file, WatchAlarm
from .notebook import parse_notebook
from .kernel import run_kernel, KernelError

class Driver(object):

    def __init__(self, notebook_path, completer):
        self.notebook_path = notebook_path
        self.completer = completer

    def get_input(self, old_name):
        name = None
        while name is None:
            try:
                name = input('>>> at {!r}; run: '.format(old_name)).strip()
            except EOFError:
                print()
                return None
            except Exception:
                print()
                raise
        return name

    def loop(self):
        watch = watch_file(self.notebook_path)

        old_name = None
        cells = None
        done = False
        while not done:
            with run_kernel(make_target) as kernel, watch:
                print(">>> starting kernel")

                while True:
                    try:
                        if watch.changed or cells is None:
                            print(">>> reloading notebook")
                            with open(self.notebook_path) as f:
                                notebook_text = f.read()
                            cells = parse_notebook(notebook_text)
                            self.completer.words = list(cells)

                        try:
                            with watch.alarm():
                                name = self.get_input(old_name)
                        except WatchAlarm:
                            print('>>> file changed during input()')
                            continue

                        if old_name is not None and old_name not in cells:
                            print(">>> cell does not exist anymore:", old_name)
                            old_name = None
                            continue

                        if name is None:
                            if confirm(">>> exit?", True):
                                done = True
                                print(">>> waiting for kernel to exit")
                                break
                            continue
                        elif not name:
                            if old_name is None:
                                continue
                            name = old_name
                        else:
                            if name not in cells:
                                print(">>> cell does not exist:", name)
                                continue
                            old_name = name

                        cell = cells[name]

                        print('>>> running {!r}'.format(name))
                        print('\n'.join('... ' + l for l in cell.splitlines()))

                        kernel(cell)

                    except KeyboardInterrupt:
                        print("^C\n>>> interrupted")

                    except KernelError:
                        if confirm(">>> kernel died; exit?"):
                            done = True
                        break


def make_target():
    locals = {}
    def target(text):
        try:
            exec(text, {}, locals)
        except Exception:
            traceback.print_exc()
    return target


def confirm(message, default=False):
    options = "Y/n" if default else "y/N"
    try:
        rv = input("{} [{}]: ".format(message, options))
        rv = rv.strip().lower()
        if not rv:
            return default
        return rv == 'y'
    except EOFError:
        print()
        return default
    except KeyboardInterrupt:
        print()
        return not default

