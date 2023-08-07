import unittest
from tests.utils import setup_test_env
setup_test_env()

from lib_comfyui.parallel_utils import IpcPayload
import multiprocessing
import queue


class TestIpcEventSharedMemoryIntegration(unittest.TestCase):
    def test_shared_memory_integration(self):
        name = "test_integration"
        expected_value = {"message": "Hello from sender!"}

        # Start the sender and receiver in separate processes
        result_queue = multiprocessing.Queue()
        receiver_ready = multiprocessing.Event()
        p1 = multiprocessing.Process(target=sender, args=(name, expected_value, receiver_ready))
        p2 = multiprocessing.Process(target=receiver, args=(name, result_queue, receiver_ready))

        p1.start()
        p2.start()

        # We expect the receiver to finish with the data from the sender
        try:
            received_data = result_queue.get(timeout=7)  # Adjust timeout as needed
            self.assertIsInstance(received_data, dict)
            self.assertEqual(received_data, expected_value)
        except queue.Empty:
            self.fail("Receiver process did not return data in time.")

        p1.join(timeout=1)
        p2.join(timeout=1)

        # Check for any lingering processes and terminate if necessary
        for p in [p1, p2]:
            if p.is_alive():
                p.terminate()


def sender(name, value, receiver_ready):
    receiver_ready.wait()
    payload = IpcPayload(name)
    payload.send(value)


def receiver(name, result_queue, receiver_ready):
    payload = IpcPayload(name)
    receiver_ready.set()
    try:
        data = payload.recv(timeout=5)
        result_queue.put(data)
        return
    except Exception as e:
        result_queue.put(e)
