import unittest
from tests import utils
utils.setup_test_env()

from lib_comfyui.parallel_utils import IpcEvent
import multiprocessing
import time


class TestIpcEventConcurrency(unittest.TestCase):
    def setUp(self):
        self.event_name = "concurrent_test_event"
        self.ipc_event = IpcEvent(name=self.event_name)

    def tearDown(self):
        self.ipc_event.stop()

    def test_different_process_inherits_state(self):
        for i in range(2):
            if i % 2 == 0:
                self.ipc_event.set()
            else:
                self.ipc_event.clear()

            result = utils.run_subprocess(__file__, get_ipc_event_state, self.event_name)
            self.assertEqual(self.ipc_event.is_set(), result)

    def test_multiple_processes_event_set(self):
        workers = 20
        with multiprocessing.Pool(processes=workers) as pool:
            results = pool.map(utils.subprocess_worker, [utils.worker_args(__file__, worker_set_event, self.event_name)] * workers)

        # All processes should return True (indicating success)
        self.assertTrue(all(results))
        self.assertTrue(self.ipc_event.is_set())

    def test_multiple_processes_event_clear(self):
        self.ipc_event.set()

        workers = 20
        with multiprocessing.Pool(processes=workers) as pool:
            results = pool.map(utils.subprocess_worker, [utils.worker_args(__file__, worker_clear_event, self.event_name)] * workers)

        # All processes should return True (indicating success)
        self.assertTrue(all(results))
        self.assertFalse(self.ipc_event.is_set())

    def test_multiple_processes_wait_for_event(self):
        assert not self.ipc_event.is_set()

        with multiprocessing.Pool(processes=5) as pool:
            # Start the subprocesses, they will wait for the event to be set
            async_results = [
                pool.apply_async(utils.subprocess_worker, [utils.worker_args(__file__, worker_wait_for_event, self.event_name)]) for
                _ in range(5)
            ]

            time.sleep(1)  # Give subprocesses a moment to start and wait for the event
            self.ipc_event.set()

            # Retrieve the results (will block until they're all available)
            results = [res.get() for res in async_results]

        # All subprocesses should have observed the event being set
        self.assertTrue(all(results))


def get_ipc_event_state(event_name):
    shared_event = IpcEvent(event_name)
    return shared_event.is_set()


def worker_set_event(event_name):
    event = IpcEvent(event_name)
    event.set()
    return True


def worker_clear_event(event_name):
    event = IpcEvent(event_name)
    event.clear()
    return True


def worker_wait_for_event(event_name):
    event = IpcEvent(event_name)
    return event.wait(timeout=5)
