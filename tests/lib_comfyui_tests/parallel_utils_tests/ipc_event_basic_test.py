import unittest
from tests.utils import setup_test_env
setup_test_env()

from unittest.mock import patch
from lib_comfyui.parallel_utils import IpcEvent


class TestIpcEventLifecycle(unittest.TestCase):
    def setUp(self):
        self.ipc_event = IpcEvent(name="test_event")

    def tearDown(self):
        # Cleanup resources
        self.ipc_event.stop()

    def test_initialization(self):
        self.assertFalse(self.ipc_event.is_set())

    def test_start_stop(self):
        self.ipc_event.start()
        self.assertTrue(self.ipc_event._alive_file is not None)
        self.assertTrue(self.ipc_event._observer is not None)

        self.ipc_event.stop()
        self.assertIsNone(self.ipc_event._alive_file)
        self.assertIsNone(self.ipc_event._observer)

    @patch.object(IpcEvent, "stop")
    def test_destruction_cleanup(self, mock_stop):
        ipc = IpcEvent(name="test_cleanup")
        del ipc
        mock_stop.assert_called_once()


class TestIpcEventSignaling(unittest.TestCase):
    def setUp(self):
        self.ipc_event = IpcEvent(name="test_signal_event")
        self.ipc_event.start()

    def tearDown(self):
        self.ipc_event.stop()

    def test_set_event(self):
        self.ipc_event.set()
        self.assertTrue(self.ipc_event.is_set())

    def test_clear_event(self):
        self.ipc_event.set()
        self.ipc_event.clear()
        self.assertFalse(self.ipc_event.is_set())

    def test_wait_with_timeout(self):
        self.ipc_event.clear()
        result = self.ipc_event.wait(timeout=0.1)
        self.assertFalse(result)

        self.ipc_event.set()
        result = self.ipc_event.wait(timeout=0.1)
        self.assertTrue(result)

    def test_event_reusability(self):
        for _ in range(5):
            self.ipc_event.set()
            self.assertTrue(self.ipc_event.is_set())

            self.ipc_event.clear()
            self.assertFalse(self.ipc_event.is_set())


class TestIpcEventObserverBehavior(unittest.TestCase):
    def setUp(self):
        self.ipc_event = IpcEvent(name="test_observer_event")
        self.ipc_event._event_path.unlink(missing_ok=True)
        self.ipc_event.start()

    def tearDown(self):
        self.ipc_event._event_path.unlink(missing_ok=True)
        self.ipc_event.stop()

    def test_observer_on_created(self):
        self.ipc_event._event_path.write_text("")
        self.assertTrue(self.ipc_event.is_set())

    def test_observer_on_deleted(self):
        self.ipc_event._event_path.unlink(missing_ok=True)
        self.assertFalse(self.ipc_event.is_set())
