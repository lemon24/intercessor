import os
import os.path
import signal
import contextlib
import time
import threading


try:
    import watchdog.observers
    import watchdog.events
except ImportError:
    watchdog = None


def alarm():
    os.kill(os.getpid(), signal.SIGALRM)

class Alarm(Exception): pass

def raise_alarm(signum, frame):
    raise Alarm


@contextlib.contextmanager
def watchdog_watch(path):
    path = os.path.abspath(path)

    def check_modification(filename):
        if filename == path:
            alarm()

    class Handler(watchdog.events.FileSystemEventHandler):

        def on_created(self, event):
            check_modification(event.src_path)

        def on_modified(self, event):
            check_modification(event.src_path)

        def on_moved(self, event):
            check_modification(event.src_path)
            check_modification(event.dest_path)

        def on_deleted(self, event):
            check_modification(event.src_path)

    observer = watchdog.observers.Observer()
    observer.schedule(Handler(), os.path.dirname(path), recursive=False)
    observer.start()

    old_signal_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, raise_alarm)
    yield
    signal.signal(signal.SIGALRM, old_signal_handler)

    observer.stop()
    observer.join()


@contextlib.contextmanager
def stat_watch(path):
    path = os.path.abspath(path)

    class Namespace(object):
        pass

    ns = Namespace()
    ns.mtime = None
    ns.done = False

    def target():
        while not ns.done:
            mtime = os.stat(path).st_mtime
            if ns.mtime is None:
                ns.mtime = mtime
                continue
            elif mtime > ns.mtime:
                ns.mtime = mtime
                alarm()
            time.sleep(1)

    t = threading.Thread(target=target)
    t.start()

    old_signal_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, raise_alarm)
    yield
    signal.signal(signal.SIGALRM, old_signal_handler)

    ns.done = True
    t.join()


if watchdog:
    watch = watchdog_watch
else:
    watch = stat_watch

