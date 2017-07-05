import sys

try:
    import readline
except ImportError:
    readline = None

from .driver import Driver


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


class DummyCompleter(object):

    def __init__(self):
        self.words = []


def main():
    notebook_path = sys.argv[1]

    completer = Completer() if readline else DummyCompleter()
    if readline:
        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')

    driver = Driver(notebook_path, completer)
    driver.loop()
