import os
import os.path
import signal
import contextlib
import time
import threading


class WatchAlarm(Exception): pass


_STOPPED = object()
_STARTED = object()
_ENABLED = object()


class BaseWatch(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self._state = _STOPPED
        self._old_signal_handler = None

    @contextlib.contextmanager
    def alarm(self):
        assert self._state is _STARTED, "not started"
        self._state = _ENABLED
        try:
            yield
        finally:
            assert self._state is _ENABLED, "not enabled"
            self._state = _STARTED

    def start(self):
        assert self._state is _STOPPED, "already started"
        self._state = _STARTED
        self._old_signal_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._signal_handler)
        self._start()

    def stop(self):
        assert self._state is _STARTED, "already stopped"
        self._stop()
        signal.signal(signal.SIGALRM, self._old_signal_handler)
        self._old_signal_handler = None
        self._state = _STOPPED

    def _start(self):
        raise NotImplementedError

    def _stop(self):
        raise NotImplementedError

    def _alarm(self):
        if self._state is _ENABLED:
            os.kill(os.getpid(), signal.SIGALRM)

    @staticmethod
    def _signal_handler(signum, frame):
        raise WatchAlarm

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class StatWatch(BaseWatch):

    def __init__(self, *args, **kwargs):
        super(StatWatch, self).__init__(*args, **kwargs)
        self._done = True
        self._mtime = None
        self._thread = None

    def _target(self):
        while not self._done:
            mtime = os.stat(self.path).st_mtime
            if self._mtime is None:
                self._mtime = mtime
                continue
            elif mtime > self._mtime:
                self._mtime = mtime
                self._alarm()
            time.sleep(1)

    def _start(self):
        self._done = False
        self._thread = threading.Thread(target=self._target)
        self._thread.start()

    def _stop(self):
        self._done = True
        self._thread.join()
        self._mtime = None
        self._thread = None


watch = StatWatch

