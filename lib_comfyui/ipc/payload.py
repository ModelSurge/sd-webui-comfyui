import contextlib
import math
import pickle
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional, Any, Callable
from lib_comfyui.ipc.strategies import IpcStrategy


class IpcPayload:
    def __init__(self, name, strategy_factory: Callable[[str], IpcStrategy], lock_directory: str = None, clear_on_init: bool = False, clear_on_del: bool = True):
        self._name = name
        self._strategy = strategy_factory(f'ipc_payload_{name}')
        lock_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        self._lock_path = Path(lock_directory, f'ipc_payload_{name}')
        self._clear_on_del = clear_on_del

        if clear_on_init:
            with self.get_lock() as lock_file:
                self._strategy.clear(lock_file)

    def __del__(self):
        if self._clear_on_del:
            lock = self.get_lock()
            with lock as lock_file:
                self._strategy.clear(lock_file)

    def get_lock(self, timeout: Optional[float] = None, mode: str = 'wb+'):
        import portalocker
        return portalocker.Lock(
            self._lock_path,
            mode=mode,
            timeout=timeout,
            check_interval=0.02,
            flags=portalocker.LOCK_EX | (portalocker.LOCK_NB * int(timeout is not None)),
        )


class IpcSender(IpcPayload):
    def send(self, value: Any):
        with self.get_lock() as lock_file:
            logging.debug(f'IPC payload {self._name}\tsend value: {value}')
            self._strategy.set_data(lock_file, pickle.dumps(value))


class IpcReceiver(IpcPayload):
    def recv(self, timeout: Optional[float] = None) -> Any:
        import portalocker
        current_time = time.time()
        end_time = (current_time + timeout) if timeout is not None else math.inf

        while current_time < end_time:
            lock = self.get_lock(timeout=end_time - current_time, mode='rb+')

            try:
                with lock as lock_file:
                    if self._strategy.is_empty(lock_file):
                        raise FileEmptyException

                    with self._strategy.get_data(lock_file) as data, restore_torch_load():
                        value = pickle.loads(data)
                        del data

                logging.debug(f'IPC payload {self._name}\treceive value: {value}')
                return value
            except FileEmptyException:
                time.sleep(lock.check_interval)  # yuck
                current_time = time.time()
                continue
            except portalocker.LockException:
                break

        raise TimeoutError


class FileEmptyException(Exception):
    pass


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

    torch.load = original_torch_load
