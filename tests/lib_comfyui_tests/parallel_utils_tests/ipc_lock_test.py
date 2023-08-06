import time
import unittest
from tests.utils import setup_test_env
setup_test_env()
from lib_comfyui.parallel_utils import IpcLock, IpcEvent
import pathlib
log_path = pathlib.Path(__file__).parent / 'logs.txt'
with open(log_path, 'w'):
    pass


from multiprocessing import Process, Value, Array
from time import sleep


def log(*message):
    with open(log_path, 'a') as log_file:
        log_file.write(" ".join(str(v) for v in message) + "\n")
        log_file.flush()


class TestIpcLock(unittest.TestCase):
    def test_acquire_timeout_waits(self):
        lock = IpcLock('test')
        timeout = 1
        with IpcLock('test'):
            start = time.time()
            lock.acquire(timeout=timeout)
            diff = time.time() - start

        self.assertGreaterEqual(diff, timeout)


if __name__ == '__main__':
    unittest.main()
