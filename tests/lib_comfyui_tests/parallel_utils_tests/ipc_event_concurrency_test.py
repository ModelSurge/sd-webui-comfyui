import unittest
from tests.utils import setup_test_env
setup_test_env()

from lib_comfyui.parallel_utils import IpcEvent
import multiprocessing
import pickle
import subprocess
import sys
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

            result = run_subprocess(get_ipc_event_state, self.event_name)
            self.assertEqual(self.ipc_event.is_set(), result)

    def test_multiple_processes_event_set(self):
        workers = 20
        with multiprocessing.Pool(processes=workers) as pool:
            results = pool.map(worker_func(run_subprocess), [worker_args(worker_set_event, self.event_name)] * workers)

        # All processes should return True (indicating success)
        self.assertTrue(all(results))
        self.assertTrue(self.ipc_event.is_set())

    def test_multiple_processes_event_clear(self):
        self.ipc_event.set()

        with multiprocessing.Pool(processes=5) as pool:
            results = pool.map(worker_func(run_subprocess), [worker_args(worker_clear_event, self.event_name)] * 5)

        # All processes should return True (indicating success)
        self.assertTrue(all(results))
        self.assertFalse(self.ipc_event.is_set())

    def test_multiple_processes_wait_for_event(self):
        assert not self.ipc_event.is_set()

        with multiprocessing.Pool(processes=5) as pool:
            # Start the subprocesses, they will wait for the event to be set
            async_results = [
                pool.apply_async(worker_func(run_subprocess), [worker_args(worker_wait_for_event, self.event_name)]) for
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


def worker_args(*args, **kwargs):
    return args, kwargs


def worker_func(func):
    return WorkerCallback(func)


class WorkerCallback:
    def __init__(self, func):
        self._func = func

    def __call__(self, args):
        args, kwargs = args
        return self._func(*args, **kwargs)


def run_subprocess(func, *args, **kwargs):
    # Read the source of the current file
    with open(__file__, 'r') as f:
        current_file_source = f.read()

    args = f"pickle.loads({pickle.dumps(args)})"
    kwargs = f"pickle.loads({pickle.dumps(kwargs)})"
    dump_func_call_source = f"pickle.dumps({func.__name__}(*{args}, **{kwargs}))"

    # Craft the command to include the entire current file source, function definition, and function execution
    command = [
        sys.executable,
        '-c',
        '\n'.join([
            f'{current_file_source}',
            f'res = {dump_func_call_source}',
            'sys.stdout.buffer.write(res)',
        ]),
    ]

    # Start the subprocess with stdout piped
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)

    # Get the output and wait for the subprocess to finish
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Subprocess failed with error code {proc.returncode} and message: {err.decode('utf-8')}")

    # Convert the pickled stdout data back to a Python object
    return pickle.loads(out)
