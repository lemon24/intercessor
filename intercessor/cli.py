import sys
import readline

from ._compat import input
from .kernel import run_kernel
from .watch import watch_file
from .driver import make_target, Driver


def confirm_terminate():
    try:
        rv = input("terminate? [y/N]: ")
        return rv.strip().lower() == 'y'
    except EOFError:
        return False
    except KeyboardInterrupt:
        return True


class Completer(object):

    def __init__(self):
        self.words = []

    def __call__(self, text, state):
        matches = [w for w in self.words if w.startswith(text)]

        try:
            rv = matches[state]
        except IndexError:
            return None

        if len(matches) == 1:
            return rv + ' '
        return rv


def main():
    notebook_path = sys.argv[1]

    completer = Completer()
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')

    watch = watch_file(notebook_path)
    driver = Driver(notebook_path, completer, watch)

    with run_kernel(make_target, driver, confirm_terminate) as kernel:
        with watch:
            kernel.parent_loop()

