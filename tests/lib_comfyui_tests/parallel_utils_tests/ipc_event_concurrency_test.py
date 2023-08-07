import unittest
from tests.utils import setup_test_env
setup_test_env()

from lib_comfyui.parallel_utils import IpcEvent
import multiprocessing
import time


class TestIpcEventConcurrency(unittest.TestCase):
    def setUp(self):
        self.event_name = "concurrent_test_event"
        self.ipc_event = IpcEvent(name=self.event_name)
        self.ipc_event.start()

    def tearDown(self):
        self.ipc_event.stop()

    def test_multiple_processes_event_set(self):
        processes = []

        # Start 5 processes that all try to set the event
        for _ in range(5):
            p = multiprocessing.Process(target=worker_set_event, args=(self.event_name,))
            processes.append(p)
            p.start()

        # Wait for all processes to finish
        for p in processes:
            p.join()

        # Check that the event has been set
        self.assertTrue(self.ipc_event.is_set())

    def test_multiple_processes_event_clear(self):
        # First, let's set the event
        self.ipc_event.set()
        self.assertTrue(self.ipc_event.is_set())

        processes = []

        # Start 5 processes that all try to clear the event
        for _ in range(5):
            p = multiprocessing.Process(target=worker_clear_event, args=(self.event_name,))
            processes.append(p)
            p.start()

        # Wait for all processes to finish
        for p in processes:
            p.join()

        # Check that the event has been cleared
        self.assertFalse(self.ipc_event.is_set())

    def test_multiple_processes_wait_for_event(self):
        processes = []
        result_queue = multiprocessing.Queue()

        # Start 5 processes that all wait for the event
        for _ in range(5):
            p = multiprocessing.Process(target=worker_wait_for_event, args=(self.event_name, result_queue))
            processes.append(p)
            p.start()

        # Sleep for a short duration to ensure all child processes are waiting
        time.sleep(1)

        # Now, set the event
        self.ipc_event.set()

        # Wait for all processes to finish with a timeout
        for p in processes:
            p.join(timeout=2)  # Wait for up to 2 seconds for the process to finish
            if p.is_alive():  # Check if the process did not finish in time
                p.terminate()  # Terminate the process
                self.fail("One of the processes did not observe the event being set in time.")

        # Check that all processes observed the event being set
        for _ in range(5):
            # This will raise an Empty exception if not all processes put a value into the queue
            self.assertTrue(result_queue.get(timeout=1))


def worker_set_event(event_name):
    event = IpcEvent(event_name)
    event.start()
    event.set()


def worker_clear_event(event_name):
    event = IpcEvent(event_name)
    event.start()
    event.clear()


def worker_wait_for_event(event_name, result_queue):
    event = IpcEvent(event_name)
    event.start()
    event.wait()
    result_queue.put(True)  # Put a value into the queue to signify this process observed the event set
