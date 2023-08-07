import unittest
from tests import utils
utils.setup_test_env()

from lib_comfyui.parallel_utils import IpcSender, IpcReceiver, IpcEvent
import multiprocessing


READY_EVENT_NAME = "test_integration_ready"
PAYLOAD_NAME = "test_integration"


class TestIpcEventSharedMemoryIntegration(unittest.TestCase):
    def test_shared_memory_integration(self):
        expected_value = {"message": "Hello from sender!"}

        # keep the event alive for the duration of the test
        _ready_event = IpcEvent(READY_EVENT_NAME)

        # Start the sender and receiver in separate processes
        with multiprocessing.Pool(processes=2) as pool:
            results = pool.map(utils.subprocess_worker, [
                utils.worker_args(__file__, sender, PAYLOAD_NAME, expected_value),
                utils.worker_args(__file__, receiver, PAYLOAD_NAME),
            ])

        # We expect the receiver to finish with the data from the sender
        received_data = results[1]
        self.assertEqual(received_data, expected_value)


def sender(name, value):
    ready_event = IpcEvent(READY_EVENT_NAME)
    ready_event.wait()
    payload = IpcSender(name)
    payload.send(value)


def receiver(name):
    ready_event = IpcEvent(READY_EVENT_NAME)
    payload = IpcReceiver(name)
    ready_event.set()
    return payload.recv(timeout=5)
