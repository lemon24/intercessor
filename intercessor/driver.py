import traceback
import contextlib

from .watch import watch_file, WatchAlarm
from .notebook import parse_notebook
from .kernel import run_kernel, KernelError
from .utils import echo, prompt, confirm


class BaseDriver(object):

    def __init__(self, notebook_path, completer):
        self.notebook_path = notebook_path
        self.completer = completer
        self.old_name = None
        self.cells = None
        self.kernel = None
        self.watch = None

    @contextlib.contextmanager
    def run_kernel(self):
        assert self.kernel is None
        try:
            with run_kernel(Target) as kernel:
                self.kernel = kernel
                yield
        finally:
            self.kernel = None

    @contextlib.contextmanager
    def run_watch(self):
        assert self.watch is None
        try:
            with watch_file(self.notebook_path) as watch:
                self.watch = watch
                yield
        finally:
            self.watch = None

    def loop(self):
        self.old_name = None
        self.cells = None
        with self.run_watch():
            while True:
                try:
                    self.notify_kernel_starting()
                    with self.run_kernel():
                        if self.command_loop():
                            self.notify_kernel_exiting()
                            break
                except KernelError:
                    if not self.confirm_restart():
                        break

    def command_loop(self):
        while True:
            try:
                if self.watch.changed or self.cells is None:
                    with open(self.notebook_path) as f:
                        notebook_text = f.read()
                    self.cells = parse_notebook(notebook_text)
                    self.completer.words = list(self.cells)
                    self.notify_notebook_reloaded()

                if self.old_name is not None and self.old_name not in self.cells:
                    self.notify_cell_gone()
                    self.old_name = None
                    continue

                try:
                    with self.watch.alarm():
                        name = self.read_command().strip()
                except EOFError:
                    if self.confirm_exit():
                        return True
                    continue
                except WatchAlarm:
                    self.notify_notebook_changed_during_input()
                    continue

                self.one_command(name)
            except KeyboardInterrupt:
                self.notify_interrupted()

    def one_command(self, name):
        if not name:
            if self.old_name is None:
                return
            name = self.old_name
        else:
            if name not in self.cells:
                self.notify_cell_does_not_exist()
                return
            self.old_name = name

        cell = self.cells[name]

        self.notify_cell_running(name, cell)
        self.kernel(cell)

    def notify_kernel_starting(self):
        pass

    def notify_kernel_exiting(self):
        pass

    def notify_notebook_reloaded(self):
        pass

    def notify_notebook_changed_during_input(self):
        pass

    def notify_cell_gone(self):
        pass

    def notify_cell_does_not_exist(self):
        pass

    def notify_cell_running(self, name, cell):
        pass

    def notify_interrupted(self):
        pass

    def read_command(self):
        return prompt(':')

    def confirm_exit(self):
        return True

    def confirm_restart(self):
        return False


class Driver(BaseDriver):

    def notify_kernel_starting(self):
        echo(">>> starting kernel")

    def notify_kernel_exiting(self):
        echo(">>> waiting for kernel to exit")

    def notify_notebook_reloaded(self):
        echo(">>> reloaded notebook")

    def notify_notebook_changed_during_input(self):
        echo()

    def notify_cell_gone(self):
        echo(">>> cell does not exist anymore:", self.old_name)

    def notify_cell_does_not_exist(self):
        echo(">>> cell does not exist:", name)

    def notify_cell_running(self, name, cell):
        echo('>>> running {!r}'.format(name))
        echo('\n'.join('... ' + l for l in cell.splitlines()))

    def notify_interrupted(self):
        echo(">>> interrupted")

    def read_command(self):
        return prompt('>>> at {!r}; run: '.format(self.old_name)).strip()

    def confirm_exit(self):
        return confirm(">>> exit?", True)

    def confirm_restart(self):
        return not confirm(">>> kernel died; exit?")


class Target(object):

    def __init__(self):
        self.context = {}

    def __call__(self, text):
        try:
            exec(text, self.context)
        except Exception:
            traceback.print_exc()

