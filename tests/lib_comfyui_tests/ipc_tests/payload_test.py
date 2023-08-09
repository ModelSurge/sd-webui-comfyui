import unittest
from tests.utils import setup_test_env, run_subprocess
setup_test_env()

import contextlib
import pickle
import time
from typing import Any, Union
from lib_comfyui.ipc_payload import IpcReceiver, IpcSender
from lib_comfyui.ipc_strategies import FileSystemIpcStrategy


class MockStrategy:
    storage = {}

    def __init__(self, name: str):
        self.name = name
        MockStrategy.storage[name] = None

    def is_empty(self, _lock_file: Any) -> bool:
        return self.storage[self.name] is None

    def set_data(self, _lock_file: Any, data: Union[bytes, bytearray, memoryview]):
        self.storage[self.name] = data

    @contextlib.contextmanager
    def get_data(self, _lock_file: Any) -> Union[bytes, bytearray, memoryview]:
        yield MockStrategy.storage[self.name]
        MockStrategy.storage[self.name] = None

    def clear(self, _lock_file: Any):
        MockStrategy.storage[self.name] = None


class TestIpcSender(unittest.TestCase):
    def test_send_method(self):
        strategy: MockStrategy
        def strategy_factory(*args):
            nonlocal strategy
            strategy = MockStrategy(*args)
            return strategy

        sender = IpcSender("test_sender", strategy_factory)
        mock_value = "test_value"
        sender.send(mock_value)

        self.assertEqual(MockStrategy.storage[strategy.name], pickle.dumps(mock_value))


class TestIpcReceiver(unittest.TestCase):
    def test_receive_method(self):
        strategy: MockStrategy
        def strategy_factory(*args):
            nonlocal strategy
            strategy = MockStrategy(*args)
            return strategy

        receiver = IpcReceiver("test_receiver", strategy_factory)

        mock_value = "test_value"
        strategy.set_data(None, pickle.dumps(mock_value))  # mock some data in the "shared memory"

        received_value = receiver.recv()
        self.assertEqual(received_value, mock_value)


class TestFunctionalIpc(unittest.TestCase):
    def setUp(self) -> None:
        self.name = "test"

    def test_basic_send_and_receive(self):
        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, "test_value")
        received_value = run_subprocess(__file__, receiver_worker, self.name, FileSystemIpcStrategy)

        self.assertEqual(received_value, "test_value")

    def test_send_and_receive_complex_objects(self):
        complex_data = {"key": ["value1", "value2"], "num": 12345}

        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, complex_data)
        received_data = run_subprocess(__file__, receiver_worker, self.name, FileSystemIpcStrategy)

        self.assertEqual(received_data, complex_data)

    def test_concurrent_sends(self):
        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, "data1")
        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, "data2")

        # Only the last data sent should be received due to overwriting
        received_data = run_subprocess(__file__, receiver_worker, self.name, FileSystemIpcStrategy)
        self.assertEqual(received_data, "data2")

    def test_mismatched_names(self):
        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, "data")

        with self.assertRaises(Exception):  # Expect an exception because names don't match
            run_subprocess(__file__, receiver_worker, "mismatched_name", FileSystemIpcStrategy)

    def test_timeout_behavior(self):
        start_time = time.time()
        with self.assertRaises(Exception):
            run_subprocess(__file__, receiver_worker, self.name, FileSystemIpcStrategy, 2)
        end_time = time.time()

        self.assertTrue(1.5 <= end_time - start_time <= 2.5)  # Ensure timeout was approximately 2 seconds

    def test_queueing_behavior(self):
        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, "data1")
        run_subprocess(__file__, sender_worker, self.name, FileSystemIpcStrategy, "data2")

        # Since the send overwrites previous data, only "data2" should be received
        received_data = run_subprocess(__file__, receiver_worker, self.name, FileSystemIpcStrategy)
        self.assertEqual(received_data, "data2")

    def test_error_scenarios(self):
        # Test receiving with no data sent
        with self.assertRaises(Exception):
            run_subprocess(__file__, receiver_worker, self.name, FileSystemIpcStrategy)


def sender_worker(name, strategy_cls, data):
    sender = IpcSender(name, strategy_cls, clear_on_init=True, clear_on_del=False)
    sender.send(data)


def receiver_worker(name, strategy_cls, timeout=1):
    receiver = IpcReceiver(name, strategy_cls)
    return receiver.recv(timeout=timeout)


if __name__ == "__main__":
    unittest.main()
