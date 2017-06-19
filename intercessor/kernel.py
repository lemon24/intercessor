import multiprocessing
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Kernel:

    Process = staticmethod(multiprocessing.Process)
    Pipe = staticmethod(multiprocessing.Pipe)


    def __init__(self, make_target, driver, confirm_terminate):
        self.make_target = make_target
        self.driver = driver
        self.confirm_terminate = confirm_terminate


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
        parent_conn, kernel_conn = self.Pipe()

        def do(arg):
            parent_conn.send(arg)
            log.info("parent: send %r", arg)
            rv = parent_conn.recv()
            log.info("parent: recv %r", rv)
            return rv

        process = self.Process(
            target=self.kernel_loop,
            args=(kernel_conn, self.make_target),
            daemon=True)
        process.start()

        while True:
            try:
                if self.driver(do):
                    break
            except KeyboardInterrupt:
                if self.confirm_terminate():
                    break

        try:
            parent_conn.send(None)
            parent_conn.close()
            log.info('parent: waiting for kernel to exit')
            process.join()
        except KeyboardInterrupt:
            log.info('parent: terminating kernel')
            process.terminate()

        log.info('parent: exiting parent loop')

