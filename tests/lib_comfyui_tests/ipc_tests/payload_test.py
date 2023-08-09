import contextlib
import unittest
from typing import Union, Any
import pickle
import time


from lib_comfyui.ipc_payload import IpcSender, IpcReceiver


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
    def test_basic_send_and_receive(self):
        sender = IpcSender("test", MockStrategy)
        receiver = IpcReceiver("test", MockStrategy)

        mock_value = "test_value"
        sender.send(mock_value)
        received_value = receiver.recv()

        self.assertEqual(received_value, mock_value)

    def test_send_and_receive_complex_objects(self):
        sender = IpcSender("test", MockStrategy)
        receiver = IpcReceiver("test", MockStrategy)

        complex_data = {"key": ["value1", "value2"], "num": 12345}
        sender.send(complex_data)
        received_data = receiver.recv()

        self.assertEqual(received_data, complex_data)

    def test_concurrent_sends(self):
        sender1 = IpcSender("test", MockStrategy)
        sender2 = IpcSender("test", MockStrategy)
        receiver = IpcReceiver("test", MockStrategy)

        sender1.send("data1")
        sender2.send("data2")

        received_data = receiver.recv()
        self.assertEqual(received_data, "data2")

    def test_mismatched_names(self):
        sender = IpcSender("sender", MockStrategy)
        receiver = IpcReceiver("receiver", MockStrategy)

        sender.send("data")
        with self.assertRaises(TimeoutError):
            receiver.recv(timeout=1)

    def test_timeout_behavior(self):
        receiver = IpcReceiver("test", MockStrategy)

        start_time = time.time()
        with self.assertRaises(TimeoutError):
            receiver.recv(timeout=2)
        end_time = time.time()

        self.assertTrue(1.5 <= end_time - start_time <= 2.5)

    def test_queueing_behavior(self):
        sender = IpcSender("test", MockStrategy)
        receiver = IpcReceiver("test", MockStrategy)

        sender.send("data1")
        sender.send("data2")

        received_data = receiver.recv()
        self.assertEqual(received_data, "data2")

    def test_error_scenarios(self):
        _sender = IpcSender("test", MockStrategy)
        receiver = IpcReceiver("test", MockStrategy)

        with self.assertRaises(TimeoutError):
            receiver.recv(timeout=1)


if __name__ == "__main__":
    unittest.main()
