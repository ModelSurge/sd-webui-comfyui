import contextlib
import hashlib
import os
import pickle
import tempfile
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Any
import portalocker


class CallbackWatcher:
    def __init__(self, callback, name: str):
        self._callback = callback
        self._res_sender = IpcSender(f'res_{name}')
        self._args_receiver = IpcReceiver(f'args_{name}')
        self._producer_thread = None

    def start(self):
        def thread_loop():
            while self._producer_thread.is_running():
                self.attend_consumer(self._callback, timeout=0.5)

        self._producer_thread = StoppableThread(target=thread_loop, daemon=True)
        self._producer_thread.start()

    def stop(self):
        if self._producer_thread is None:
            return

        self._producer_thread.join()
        self._producer_thread = None

    def is_running(self):
        return self._producer_thread and self._producer_thread.is_running()

    def attend_consumer(self, callback, timeout: float = None):
        try:
            args, kwargs = self._args_receiver.recv(timeout=timeout)
        except TimeoutError:
            return

        try:
            self._res_sender.send(callback(*args, **kwargs))
        except Exception as e:
            self._res_sender.send(RemoteError(e))


class CallbackProxy:
    def __init__(self, name):
        self._res_receiver = IpcReceiver(f'res_{name}')
        self._args_sender = IpcSender(f'args_{name}')

    def get(self, args=None, kwargs=None):
        self._args_sender.send((args if args is not None else (), kwargs if kwargs is not None else {}))
        res = self._res_receiver.recv()
        if isinstance(res, RemoteError):
            raise res.error from res
        else:
            return res


class RemoteError(Exception):
    def __init__(self, error):
        self.error = error


class StoppableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def join(self, *args, **kwargs) -> None:
        self.stop()
        super().join(*args, **kwargs)

    def is_running(self):
        return not self._stop_event.is_set()


class IpcSender:
    def __init__(self, name, lock_directory=None):
        self._name = name
        event_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        self._lock_path = Path(event_directory, f'ipc-payload-{name}')

    def get_lock(self, timeout: Optional[float] = None):
        return portalocker.Lock(self._lock_path, mode='wb+', timeout=timeout if timeout is not None else 2 ** 8)

    def send(self, value: Any):
        with self.get_lock() as f:
            logging.debug(f'IPC payload {self._name}\tsend value: {value}')
            f.write(pickle.dumps(value))


class IpcReceiver:
    def __init__(self, name, lock_directory=None):
        self._name = name
        event_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        self._lock_path = Path(event_directory, f'ipc-payload-{name}')
        try:
            self.recv(0)
        except TimeoutError:
            pass

    def get_lock(self, timeout: Optional[float] = None):
        return portalocker.Lock(self._lock_path, mode='ab+', timeout=timeout if timeout is not None else 2 ** 8)

    def recv(self, timeout: Optional[float] = None) -> Any:
        current_time = time.time()
        end = current_time + (timeout if timeout is not None else 2 ** 8)
        while current_time < end:
            time.sleep(0.01)  # yuck
            with self.get_lock() as f:
                f.seek(0, os.SEEK_END)
                if f.tell() == 0:
                    current_time = time.time()
                    continue

                f.seek(0)
                data = f.read()
                f.seek(0)
                f.truncate()

            with restore_torch_load():
                value = pickle.loads(data)

            logging.debug(f'IPC payload {self._name}\treceive value: {value}')
            return value

        raise TimeoutError


@contextlib.contextmanager
def restore_torch_load():
    from lib_comfyui import ipc
    import torch
    original_torch_load = torch.load

    if ipc.current_process_id == 'webui':
        try:
            from modules import safe
            torch.load = safe.unsafe_torch_load
            del safe
        except ImportError:
            pass

    yield

    if torch.load != original_torch_load:
        torch.load = original_torch_load


def to_pathable_str(txt_name: str) -> str:
    return hashlib.sha256(txt_name.encode()).hexdigest()
