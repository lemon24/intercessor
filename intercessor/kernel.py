import multiprocessing
import sys
import logging

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

    def __init__(self, make_target, driver, confirm_terminate, debug=False):
        self.make_target = make_target
        self.driver = driver
        self.confirm_terminate = confirm_terminate
        self.debug = debug
        self.parent_conn = None
        self.kernel_conn = None
        self.process = None
        self.debug_handler = None
        self.old_log_level = None

    @classmethod
    def kernel_loop(cls, conn, make_target, debug):
        if debug:
            log.addHandler(cls.make_debug_handler())
            log.setLevel(logging.DEBUG)

        target = make_target()

        done = False
        while not done:

            try:
                while True:
                    arg = conn.recv()
                    log.info("kernel: recv")
                    if arg is None:
                        done = True
                        break

                    try:
                        rv = target(arg)
                    except Exception as e:
                        log.exception('kernel: exception during target')
                        rv = None

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

            except KeyboardInterrupt:
                log.info("kernel: interrupted")
                pass

        conn.close()
        log.info("kernel: exiting kernel loop")

    def parent_loop(self):
        def do(arg):
            self.parent_conn.send(arg)
            log.info("parent: send")

            while not self.parent_conn.poll(.1):
                if not self.process.is_alive():
                    log.info("parent: kernel died")
                    raise KernelError("kernel died")

            rv = self.parent_conn.recv()
            log.info("parent: recv")
            return rv

        while True:
            try:
                if self.driver(do):
                    break
            except KeyboardInterrupt:
                if self.confirm_terminate():
                    break

    def __enter__(self):
        self.parent_conn, self.kernel_conn = self.Pipe()

        self.process = self.Process(
            target=self.kernel_loop,
            args=(self.kernel_conn, self.make_target, self.debug))
        self.process.start()

        if self.debug:
            self.debug_handler = self.make_debug_handler()
            log.addHandler(self.debug_handler)
            self.old_log_level = log.level
            log.setLevel(logging.DEBUG)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.parent_conn.send(None)
            self.parent_conn.close()
            log.info('parent: waiting for kernel to exit')
            self.process.join()
        except KeyboardInterrupt:
            log.info('parent: terminating kernel')
            self.process.terminate()

        log.info('parent: exiting parent loop')

        if self.debug:
            log.setLevel(self.old_log_level)
            self.old_log_level = None
            log.removeHandler(self.debug_handler)
            self.debug_handler = None

        return False


run_kernel = Kernel

