import sys
import readline

from ._compat import input
from .kernel import Kernel
from .notebook import make_target
from .watch import watch_file
from .driver import Driver


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

    k = Kernel(
        make_target,
        Driver(notebook_path, completer, watch_file(notebook_path)),
        confirm_terminate)
    k.parent_loop()

