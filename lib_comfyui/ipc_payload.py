import contextlib
import dataclasses
import os
import pickle
import portalocker
import tempfile
import time
import logging
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
from typing import Optional, Any, IO, Union


class IpcPayload:
    def __init__(self, name, strategy, lock_directory=None):
        self._name = name
        self._strategy = strategy
        lock_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        self._lock_path = Path(lock_directory, f'ipc_payload_{name}')
        with self.get_lock() as lock_file:
            self._strategy.clear(lock_file)

    def get_lock(self, timeout: Optional[float] = None, mode: str = 'ab+'):
        return portalocker.Lock(self._lock_path, mode=mode, timeout=timeout if timeout is not None else 2 ** 8)


class IpcSender(IpcPayload):
    def send(self, value: Any):
        with self.get_lock(mode='wb+') as lock_file:
            print(f'IPC payload {self._name}\tsend value: {value}')
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

                print(f'IPC payload {self._name}\treceive value: {value}')
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


class FileSystemIpcStrategy:
    def is_empty(self, lock_file: IO) -> bool:
        lock_file.seek(0, os.SEEK_END)
        return lock_file.tell() == 0

    def set_data(self, lock_file: IO, data: Union[bytes, bytearray, memoryview]):
        lock_file.write(data)

    @contextlib.contextmanager
    def get_data(self, lock_file: IO) -> Union[bytes, bytearray, memoryview]:
        lock_file.seek(0)
        yield lock_file.read()
        self.clear(lock_file)

    def clear(self, lock_file: IO):
        lock_file.seek(0)
        lock_file.truncate()


class SharedMemoryIpcStrategy:
    def __init__(self, shm_name: str):
        self._shm_name = shm_name
        self._shm = None

    @dataclasses.dataclass
    class Metadata:
        is_empty: bool
        size: int

    def _get_metadata(self, lock_file: IO) -> Metadata:
        file_size = lock_file.seek(0, os.SEEK_END)
        if file_size == 0:
            return self.Metadata(is_empty=True, size=0)

        lock_file.seek(0)
        return pickle.loads(lock_file.read())

    def _set_metadata(self, lock_file: IO, metadata: Metadata):
        lock_file.seek(0)
        lock_file.write(pickle.dumps(metadata))
        lock_file.truncate()

    def is_empty(self, lock_file: IO) -> bool:
        return self._get_metadata(lock_file).is_empty

    def set_data(self, lock_file: IO, data: Union[bytes, bytearray, memoryview]):
        metadata = self._get_metadata(lock_file)
        assert metadata.is_empty, f'data of shared memory IPC payload {self._shm_name} has not yet been read'

        data_len = len(data)
        self._clear_shm()
        self._shm = SharedMemory(name=self._shm_name, create=True, size=data_len)
        self._shm.buf[:data_len] = data
        self._set_metadata(lock_file, self.Metadata(is_empty=False, size=data_len))

    @contextlib.contextmanager
    def get_data(self, lock_file: IO) -> Union[bytes, bytearray, memoryview]:
        metadata = self._get_metadata(lock_file)
        assert not metadata.is_empty, f'metadata not found for shared memory IPC payload {self._shm_name}'

        print(f'trying to read IPC payload {self._shm_name}...')
        shm = SharedMemory(name=self._shm_name)
        yield shm.buf[:metadata.size]
        shm.close()
        shm.unlink()
        self.clear(lock_file)

    def clear(self, lock_file: IO):
        self._set_metadata(lock_file, self.Metadata(is_empty=True, size=0))

    def _clear_shm(self):
        try:
            if self._shm is None:
                self._shm = SharedMemory(name=self._shm_name)
            self._shm.close()
            self._shm.unlink()
        except FileNotFoundError:
            pass
        finally:
            self._shm = None


if os.name == 'nt':
    OsIpcStrategy = SharedMemoryIpcStrategy
else:
    OsIpcStrategy = lambda *args, **kwargs: FileSystemIpcStrategy()


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
