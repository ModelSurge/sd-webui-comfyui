import hashlib
import multiprocessing.shared_memory
import pickle
import tempfile
import threading
from pathlib import Path
from typing import Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CallbackWatcher:
    def __init__(self, callback, name: str):
        self._callback = callback
        self._queue = CallbackQueue(name)
        self._producer_thread = None

    def start(self):
        def thread_loop():
            while self._producer_thread.is_running():
                self._queue.attend_consumer(self._callback, timeout=0.5)

        self._queue.start()
        self._producer_thread = StoppableThread(target=thread_loop, daemon=True)
        self._producer_thread.start()

    def stop(self):
        if self._producer_thread is None:
            return

        self._producer_thread.join()
        self._producer_thread = None
        self._queue.stop()

    def is_running(self):
        return self._producer_thread and self._producer_thread.is_running()


class CallbackQueue:
    def __init__(self, name):
        self._consumer_ready_event = IpcEvent(f'{CallbackQueue.__name__}_consumer_ready_event_{name}')
        self._res_payload = IpcPayload(f'{CallbackQueue.__name__}_res_payload_{name}')
        self._args_payload = IpcPayload(f'{CallbackQueue.__name__}_args_payload_{name}')
        self._lock = IpcLock(f'{CallbackQueue.__name__}_lock_{name}')

    def start(self):
        self._lock.start()
        self._consumer_ready_event.start()
        self._res_payload.start()
        self._args_payload.start()

    def stop(self):
        self._args_payload.stop()
        self._res_payload.stop()
        self._consumer_ready_event.stop()
        self._lock.stop()

    def attend_consumer(self, callback, timeout: float = None):
        consumer_ready = self.wait_for_consumer(timeout)
        if not consumer_ready: return
        args, kwargs = self._args_payload.recv()
        try:
            self._res_payload.send(callback(*args, **kwargs))
        except Exception as e:
            self._res_payload.send(RemoteError(e))

    def wait_for_consumer(self, timeout: float = None):
        consumer_ready = self._consumer_ready_event.wait(timeout)
        if consumer_ready:
            self._consumer_ready_event.clear()

        return consumer_ready

    def get(self, args=None, kwargs=None):
        with self._lock:
            self._args_payload.send((args if args is not None else (), kwargs if kwargs is not None else {}))
            self._consumer_ready_event.set()
            res = self._res_payload.recv()

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


class IpcPayload:
    def __init__(self, name):
        self._name = name
        self._shm = None
        self._lock = IpcLock(f"{IpcPayload.__name__}_lock_{name}")
        self._memory_event = IpcEvent(f"{IpcPayload.__name__}_memory_event_{name}")
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self._lock.start()
        self._memory_event.start()

    def stop(self):
        self._memory_event.stop()
        self._lock.stop()

    def send(self, value: Any):
        with self._lock:
            data = pickle.dumps(value)
            if self._shm:
                self._shm.close()
                self._shm.unlink()

            self._shm = multiprocessing.shared_memory.SharedMemory(f"{IpcPayload.__name__}_lock_{self._name}", create=True, size=len(data))
            self._shm.buf[:] = data
            self._memory_event.set()

    def recv(self, timeout: Optional[float] = None) -> Any:
        with self._lock:
            self._memory_event.wait(timeout=timeout)

            if self._shm:
                shm_needs_unlink = True
            else:
                self._shm = multiprocessing.shared_memory.SharedMemory(f"{IpcPayload.__name__}_lock_{self._name}")
                shm_needs_unlink = False

            with RestoreTorchLoad():
                value = pickle.loads(self._shm.buf)

            self._shm.close()
            if shm_needs_unlink:
                self._shm.unlink()

            self._shm = None
            self._memory_event.clear()
        return value


class RestoreTorchLoad:
    def __enter__(self):
        import torch
        self.original_torch_load = torch.load

        try:
            from modules import safe
            torch.load = safe.unsafe_torch_load
        except ImportError:
            pass

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import torch
        if torch.load != self.original_torch_load:
            torch.load = self.original_torch_load


class IpcEvent:
    def __init__(self, name, event_directory=None):
        self._name = name
        self._event_directory = tempfile.gettempdir() if event_directory is None else event_directory
        unique_token = hashlib.sha256(name.encode()).hexdigest()
        self._event_path = Path(self._event_directory, 'ipcevent-' + unique_token + '.event')
        self._alive_path = Path(self._event_directory, 'ipclock-alive-' + unique_token + '.lifetime')
        self._alive_file = None

        self._lock = IpcLock(f'{IpcEvent.__name__}_lock_{name}')
        self._event = threading.Event()
        self._observer = None

        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self._event.clear()
        event_handler = _IpcEventFileHandler(str(self._event_path), self._event)
        self._observer = Observer()
        self._observer.schedule(event_handler, path=self._event_directory, recursive=False)
        self._observer.start()

        with self._lock:
            try:
                self._alive_path.unlink()
                self._event_path.unlink(missing_ok=True)
                with open(self._alive_path, 'x'): pass
                self._alive_file = open(self._alive_path, 'a')
            except PermissionError:
                self._alive_file = open(self._alive_path, 'a')
                if self._event_path.exists():
                    self._event.set()
            except FileNotFoundError:
                self._event_path.unlink(missing_ok=True)
                with open(self._alive_path, 'x'): pass
                self._alive_file = open(self._alive_path, 'a')

    def stop(self):
        if self._alive_file is not None:
            self._alive_file.close()
            self._alive_file = None

        if self._lock:
            with self._lock:
                try:
                    self._alive_path.unlink(missing_ok=True)
                except PermissionError:
                    pass

        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        self._lock.stop()

    def set(self):
        with self._lock, open(self._event_path, 'a'):
            pass

    def clear(self):
        with self._lock:
            self._event_path.unlink(missing_ok=True)

    def is_set(self):
        with self._lock:
            return self._event_path.exists()

    def wait(self, timeout=None):
        return self._event.wait(timeout)


class _IpcEventFileHandler(FileSystemEventHandler):
    def __init__(self, filepath, event):
        self._filepath = filepath
        self._event = event

    def on_created(self, event):
        if event.src_path == str(self._filepath):
            self._event.set()

    def on_deleted(self, event):
        if event.src_path == str(self._filepath):
            self._event.clear()


class IpcLock:
    def __init__(self, name, lock_directory=None):
        self._name = name
        self._lock_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        unique_token = hashlib.sha256(name.encode()).hexdigest()
        self._lock_path = Path(self._lock_directory, 'ipclock-' + unique_token + '.lock')
        self._lock_file = None
        self._observer = None

        self._lock_event = threading.Event()
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self._lock_event.set()
        event_handler = _IpcLockFileHandler(str(self._lock_path), self._lock_event)
        self._observer = Observer()
        self._observer.schedule(event_handler, path=self._lock_directory, recursive=False)
        self._observer.start()

        # collapse system-wide state and align events
        if self.is_locked():
            # close the lock if it was accidentally left locked by previous usage
            try:
                # if no other process has the file open, collapse the state
                # missing_ok=True for the case where another process was holding a reference but closed it since then
                self._lock_path.unlink(missing_ok=True)
            except PermissionError:
                # another process is holding the lock, so the state is valid
                # safely call self._lock_event.clear() using the fs observer
                with self:
                    pass

    def stop(self):
        if not self.is_started():
            return

        self._observer.stop()
        self._observer.join()
        self._observer = None

    def is_started(self):
        return self._observer is not None

    def is_locked(self):
        if self.is_acquired():
            return True

        try:
            with open(self._lock_path, 'x'):
                pass
            self.release()
            return False
        except FileExistsError:
            return True

    def is_acquired(self):
        return self._lock_file is not None

    def acquire(self, timeout=None):
        while True:
            if self._lock_event.wait(timeout):
                try:
                    self._lock_file = open(self._lock_path, 'x')
                    return True
                except (FileExistsError, PermissionError):
                    continue
            else:
                return False

    def release(self):
        if self._lock_file is not None:
            self._lock_file.close()
            self._lock_file = None
        while True:
            try:
                self._lock_path.unlink(missing_ok=True)
                return
            except PermissionError:
                continue

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.release()


class _IpcLockFileHandler(FileSystemEventHandler):
    def __init__(self, filepath, lock_event):
        self._filepath = filepath
        self._lock_event = lock_event

    def on_created(self, event):
        if event.src_path == self._filepath:
            self._lock_event.clear()

    def on_deleted(self, event):
        if event.src_path == self._filepath:
            self._lock_event.set()
