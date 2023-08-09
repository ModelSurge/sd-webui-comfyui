import contextlib
import dataclasses
import os
import pickle
from multiprocessing.shared_memory import SharedMemory
from typing import IO, Union


__all__ = [
    'FileSystemIpcStrategy',
    'SharedMemoryIpcStrategy',
    'OsFriendlyIpcStrategy',
]


class FileSystemIpcStrategy:
    def __init__(self, *args, **kwargs):
        pass

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


BytesLike = Union[bytes, bytearray, memoryview]


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

    def set_data(self, lock_file: IO, data: BytesLike):
        metadata = self._get_metadata(lock_file)
        assert metadata.is_empty, f'data of shared memory IPC payload {self._shm_name} has not yet been read'

        data_len = len(data)
        self._clear_shm()
        self._shm = SharedMemory(name=self._shm_name, create=True, size=data_len)
        self._shm.buf[:data_len] = data
        self._set_metadata(lock_file, self.Metadata(is_empty=False, size=data_len))

    @contextlib.contextmanager
    def get_data(self, lock_file: IO) -> BytesLike:
        metadata = self._get_metadata(lock_file)
        assert not metadata.is_empty, f'metadata not found for shared memory IPC payload {self._shm_name}'

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

        self._shm = None


if os.name == 'nt':
    class OsFriendlyIpcStrategy(SharedMemoryIpcStrategy):
        pass
else:
    class OsFriendlyIpcStrategy(FileSystemIpcStrategy):
        pass
