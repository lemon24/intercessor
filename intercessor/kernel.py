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

    def __init__(self, make_target, driver, confirm_terminate):
        self.make_target = make_target
        self.driver = driver
        self.confirm_terminate = confirm_terminate
        self.parent_conn = None
        self.kernel_conn = None
        self.process = None

    @classmethod
    def kernel_loop(cls, conn, make_target):
        target = make_target()

        done = False
        while not done:

            try:
                while True:
                    i = conn.recv()
                    log.info("kernel: recv %r", i)
                    if i is None:
                        done = True
                        break

                    i = target(i)

                    conn.send(i)
                    log.info("kernel: send %r", i)

            except KeyboardInterrupt:
                log.info("kernel: interrupted")
                pass

        conn.close()
        log.info("kernel: exiting kernel loop")

    def parent_loop(self):
        def do(arg):
            self.parent_conn.send(arg)
            log.info("parent: send %r", arg)
            rv = self.parent_conn.recv()
            log.info("parent: recv %r", rv)
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
            args=(self.kernel_conn, self.make_target))
        self.process.start()

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
        return False


run_kernel = Kernel

