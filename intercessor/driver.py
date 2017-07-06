from __future__ import print_function
import traceback

from .watch import watch_file, WatchAlarm
from .notebook import parse_notebook
from .kernel import run_kernel, KernelError
from .utils import prompt, confirm

class Driver(object):

    def __init__(self, notebook_path, completer):
        self.notebook_path = notebook_path
        self.completer = completer
        self.old_name = None
        self.cells = None

    def loop(self):
        watch = watch_file(self.notebook_path)
        self.old_name = None
        self.cells = None
        while True:
            try:
                with run_kernel(Target) as kernel, watch:
                    print(">>> starting kernel")
                    if self.command_loop(kernel, watch):
                        print(">>> waiting for kernel to exit")
                        break
            except KernelError:
                if confirm(">>> kernel died; exit?"):
                    break

    def command_loop(self, kernel, watch):
        while True:
            try:
                if watch.changed or self.cells is None:
                    print(">>> reloading notebook")
                    with open(self.notebook_path) as f:
                        notebook_text = f.read()
                    self.cells = parse_notebook(notebook_text)
                    self.completer.words = list(self.cells)

                try:
                    with watch.alarm():
                        try:
                            name = prompt('>>> at {!r}; run: '.format(self.old_name)).strip()
                        except EOFError:
                            name = None
                except WatchAlarm:
                    print('>>> file changed during input()')
                    continue

                if self.old_name is not None and self.old_name not in self.cells:
                    print(">>> cell does not exist anymore:", self.old_name)
                    self.old_name = None
                    continue

                if name is None:
                    if confirm(">>> exit?", True):
                        return True
                    continue
                elif not name:
                    if self.old_name is None:
                        continue
                    name = self.old_name
                else:
                    if name not in self.cells:
                        print(">>> cell does not exist:", name)
                        continue
                    self.old_name = name

                cell = self.cells[name]

                print('>>> running {!r}'.format(name))
                print('\n'.join('... ' + l for l in cell.splitlines()))

                kernel(cell)
            except KeyboardInterrupt:
                print(">>> interrupted")


class Target(object):

    def __init__(self):
        self.context = {}

    def __call__(self, text):
        try:
            exec(text, self.context)
        except Exception:
            traceback.print_exc()

