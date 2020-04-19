import multiprocessing
import sys
import logging
import signal

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Use the 'spawn' start method if available; "safely forking a multithreaded
# process is problematic", and we are using multiple threads.
if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
    multiprocessing = multiprocessing.get_context('spawn')


class KernelError(Exception): pass


class Kernel(object):

    Process = staticmethod(multiprocessing.Process)
    Pipe = staticmethod(multiprocessing.Pipe)

    make_debug_handler = staticmethod(lambda: logging.StreamHandler())

    def __init__(self, make_target, debug=False):
        self.make_target = make_target
        self.debug = debug
        self._parent_conn = None
        self._kernel_conn = None
        self._process = None
        self._debug_handler = None
        self._old_log_level = None

    @classmethod
    def _kernel_loop(cls, conn, make_target, debug):
        if debug:
            log.addHandler(cls.make_debug_handler())
            log.setLevel(logging.DEBUG)

        target = make_target()

        # When SIGINT is sent to the parent, all processes in its
        # process group receive it. By default, SIGINT manifests as a
        # KeyboardInterrupt being raised.
        #
        # On Linux, wrapping the whole "while True:" in a try/except
        # KeyboardInterrupt is enough to handle it.
        #
        # On Darwin (macOS), however, we get a second KeyboardInterrupt
        # in the exception handler for the first one (?).
        # In order to handle this, we ignore SIGINT in "kernel mode"
        # and use the default handler only in "user mode",
        # i.e. while running target.
        old_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            done = False
            while not done:

                    while True:
                        args_tuple = conn.recv()
                        log.info("kernel: recv")
                        if args_tuple is None:
                            done = True
                            break

                        args, kwargs = args_tuple

                        signal.signal(signal.SIGINT, old_sigint_handler)
                        try:
                            rv = target(*args, **kwargs)
                        except Exception as e:
                            log.exception('kernel: exception during target')
                            rv = None
                        except KeyboardInterrupt:
                            log.info("kernel: interrupted during target")
                            continue
                        finally:
                            signal.signal(signal.SIGINT, signal.SIG_IGN)

                        # We assume that the actual send never fails and that any
                        # exceptions are raised during the pickling of rv prior
                        # to sending it. I don't know how to distinguish between
                        # pickling errors and actual send errors (without trying
                        # to pickle rv before sending it). Even if I did, I'm not
                        # sure how to recover from a failed actual send.
                        try:
                            conn.send(rv)
                            log.info('kernel: send')
                        except Exception as e:
                            log.exception('kernel: exception during send')
                            conn.send(None)
                            log.info("kernel: send")

        finally:
            signal.signal(signal.SIGINT, old_sigint_handler)

        # TODO: Should this be in finally: too?
        conn.close()
        log.info("kernel: exiting kernel loop")

    def __call__(self, *args, **kwargs):
        assert self._process, "not started"
        assert self._process.is_alive(), "not alive"
        assert not self._parent_conn.closed, "closed"

        self._parent_conn.send((args, kwargs))
        log.info("parent: send")

        while not self._parent_conn.poll(.1):
            if not self._process.is_alive():
                log.info("parent: kernel died")
                self._parent_conn.close()
                raise KernelError("kernel died")

        rv = self._parent_conn.recv()
        log.info("parent: recv")
        return rv

    def start(self):
        assert not self._process or not self._process.is_alive(), "already started"

        if self.debug:
            self._debug_handler = self.make_debug_handler()
            log.addHandler(self._debug_handler)
            self._old_log_level = log.level
            log.setLevel(logging.DEBUG)

        self._parent_conn, self._kernel_conn = self.Pipe()

        self._process = self.Process(
            target=self._kernel_loop,
            args=(self._kernel_conn, self.make_target, self.debug))
        self._process.start()

    def close(self):
        assert self._process, "not started"
        try:
            if not self._parent_conn.closed:
                self._parent_conn.send(None)
                log.info('parent: send None')
                self._parent_conn.close()
        except OSError:
            pass

    def terminate(self):
        assert self._process, "not stared"
        self._process.terminate()

    def join(self):
        assert self._process, "not started"
        self._process.join()
        if self.debug:
            log.setLevel(self._old_log_level)
            self._old_log_level = None
            log.removeHandler(self._debug_handler)
            self._debug_handler = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
            log.info('parent: waiting for kernel to exit')
            self.join()
        except KeyboardInterrupt:
            log.info('parent: terminating kernel')
            self.terminate()
            self.join()
        return False


run_kernel = Kernel

