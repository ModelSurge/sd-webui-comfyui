import contextlib
import pickle
import portalocker
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional, Any


class IpcPayload:
    def __init__(self, name, strategy_factory, lock_directory=None):
        self._name = name
        self._strategy = strategy_factory(f'ipc_payload_{name}')
        lock_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        self._lock_path = Path(lock_directory, f'ipc_payload_{name}')
        with self.get_lock() as lock_file:
            self._strategy.clear(lock_file)

    def get_lock(self, timeout: Optional[float] = None, mode: str = 'ab+'):
        return portalocker.Lock(
            self._lock_path,
            mode=mode,
            timeout=timeout if timeout is not None else 2 ** 8,
            check_interval=0.01,
        )


class IpcSender(IpcPayload):
    def send(self, value: Any):
        with self.get_lock(mode='wb+') as lock_file:
            logging.debug(f'IPC payload {self._name}\tsend value: {value}')
            self._strategy.set_data(lock_file, pickle.dumps(value))


class IpcReceiver(IpcPayload):
    def recv(self, timeout: Optional[float] = None) -> Any:
        current_time = time.time()
        end_time = current_time + (timeout if timeout is not None else 2 ** 8)

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

    if torch.load != original_torch_load:
        torch.load = original_torch_load
