import threading
import os
import signal
import time
from datetime import datetime, timedelta

import pytest

from intercessor.kernel import run_kernel, KernelError


def setup_module(module):
    # Become process leader, so tox doesn't get the any SIGINTs.
    try:
        os.setsid()
    except OSError:
        # Process is already process leader.
        pass


def make_double():
    def double(i):
        return i * 2
    return double

def test_kernel():
    kernel = run_kernel(make_double)
    with pytest.raises(Exception):
        kernel(1)
    with kernel:
        assert kernel(2) == 4
        assert kernel(3) == 6
    with pytest.raises(Exception):
        kernel(4)
    with kernel:
        kernel(5)


def make_raise_exception():
    def raise_exception():
        raise RuntimeError
    return raise_exception

def test_kernel_exception():
    with run_kernel(make_raise_exception) as kernel:
        assert kernel() is None


def make_return_unpickleable():
    def return_unpickleable():
        return lambda: None
    return return_unpickleable

def test_kernel_unpickleable():
    with run_kernel(make_return_unpickleable) as kernel:
        assert kernel() is None


def make_kill_self():
    def kill_self():
        import os, signal
        os.kill(os.getpid(), signal.SIGTERM)
    return kill_self

def test_kernel_death():
    with run_kernel(make_kill_self) as kernel:
        with pytest.raises(KernelError):
            kernel()


def interrupt():
    os.killpg(0, signal.SIGINT)


def make_sleep():
    def sleep():
        time.sleep(10)
    return sleep

def test_kernel_interrupt():
    with run_kernel(make_sleep) as kernel:
        start = datetime.now()
        threading.Timer(1, interrupt).start()
        with pytest.raises(KeyboardInterrupt):
            kernel()
        end = datetime.now()
        assert end - start < timedelta(seconds=2)


def make_sleep_forever():
    def sleep_forever():
        while True:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                pass
    return sleep_forever

def test_kernel_terminate():
    with run_kernel(make_sleep_forever) as kernel:
        start = datetime.now()
        threading.Timer(1, interrupt).start()
        threading.Timer(2, interrupt).start()
        with pytest.raises(KeyboardInterrupt):
            kernel()
        end = datetime.now()
        assert end - start < timedelta(seconds=3)

