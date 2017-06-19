import sys
import readline

from .kernel import Kernel
from .notebook import make_target, make_driver


def confirm_terminate():
    try:
        rv = input("terminate? [y/N]: ")
    except EOFError:
        return False
    except KeyboardInterrupt:
        return True


class Completer:

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
    completer = Completer()
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')

    k = Kernel(make_target, make_driver(sys.argv[1], completer), confirm_terminate)
    k.parent_loop()

