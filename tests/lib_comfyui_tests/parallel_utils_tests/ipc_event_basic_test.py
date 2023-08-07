import unittest
from tests import utils
utils.setup_test_env()

from unittest.mock import patch
from lib_comfyui.parallel_utils import IpcEvent


class TestIpcEventLifecycle(unittest.TestCase):
    def setUp(self):
        self.name = "test_event"
        self.ipc_event = IpcEvent(self.name)

    def tearDown(self):
        self.ipc_event.stop()

    def test_initialization(self):
        self.assertFalse(self.ipc_event.is_set())

    def test_auto_start(self):
        self.assertIsNotNone(self.ipc_event._alive_file)
        self.assertIsNotNone(self.ipc_event._observer)

    def test_start_stop(self):
        self.ipc_event.stop()
        self.assertIsNone(self.ipc_event._alive_file)
        self.assertIsNone(self.ipc_event._observer)

        self.ipc_event.start()
        self.assertIsNotNone(self.ipc_event._alive_file)
        self.assertIsNotNone(self.ipc_event._observer)

    @patch.object(IpcEvent, "stop")
    def test_destruction_cleanup(self, mock_stop):
        IpcEvent(name="test_cleanup")
        mock_stop.assert_called_once()

    def test_inherit_state(self):
        self.ipc_event.set()
        shared_event = IpcEvent(self.name).set()
        self.assertTrue(shared_event.is_set())

    def test_new_instance_alter_state(self):
        IpcEvent(self.name).set()
        self.assertTrue(self.ipc_event.is_set())


class TestIpcEventSignaling(unittest.TestCase):
    def setUp(self):
        self.name = "test_signal_event"
        self.ipc_event = IpcEvent(self.name)

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
        self.ipc_event.stop()
        self.ipc_event._event_path.unlink(missing_ok=True)
        self.ipc_event.start()

    def tearDown(self):
        self.ipc_event._event_path.unlink(missing_ok=True)
        self.ipc_event.stop()

    def test_observer_on_created(self):
        self.ipc_event._event_path.write_text("")
        self.assertTrue(self.ipc_event.is_set())
        self.ipc_event._event_path.unlink(missing_ok=True)
        self.assertFalse(self.ipc_event.is_set())
