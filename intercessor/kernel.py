import multiprocessing
import sys
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Use the 'spawn' start method if available; "safely forking a multithreaded
# process is problematic", and we are using multiple threads.
if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
    multiprocessing = multiprocessing.get_context('spawn')


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
                    i = conn.recv()
                    log.info("kernel: recv")
                    if i is None:
                        done = True
                        break

                    i = target(i)

                    conn.send(i)
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

