import hashlib
import pickle
import tempfile
import threading
from pathlib import Path
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
        with self._lock:
            self._consumer_ready_event.start()
            self._args_payload.start()
            self._res_payload.start()

    def stop(self):
        with self._lock:
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
    def __init__(self, name, payload_directory=None):
        self._payload_directory = tempfile.gettempdir() if payload_directory is None else payload_directory
        unique_token = hashlib.sha256(name.encode()).hexdigest()
        self._filepath = Path(self._payload_directory, 'ipcpayload-' + unique_token + '.payload')
        self._lock = IpcLock(f"{IpcPayload.__name__}_lock_{name}")
        self._memory_event = IpcEvent(f"{IpcPayload.__name__}_memory_event_{name}")

    def start(self):
        self._lock.start()
        with self._lock:
            self._memory_event.start()
            self._filepath.unlink(missing_ok=True)

    def stop(self):
        with self._lock:
            self._memory_event.start()

        self._lock.stop()

    def send(self, value: object):
        with self._lock:
            self._filepath.unlink(missing_ok=True)
            with RestoreTorchLoad():
                data = pickle.dumps(value)

            with open(str(self._filepath), 'bx') as f:
                f.write(data)

            self._memory_event.set()

    def recv(self, timeout=None) -> object:
        self._memory_event.wait(timeout=timeout)
        with self._lock:
            with open(str(self._filepath), 'br') as f:
                data = f.read()

            self._memory_event.clear()
            self._filepath.unlink(missing_ok=True)

        with RestoreTorchLoad():
            return pickle.loads(data)


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
        self._filepath = Path(self._event_directory, 'ipcevent-' + unique_token + '.event')
        self._event_handler = None
        self._observer = None
        self._lock = IpcLock(f'{IpcEvent.__name__}_lock_{name}')

    def start(self):
        self._event_handler = _IpcEventFileHandler(self._filepath)
        self._observer = Observer()
        self._observer.schedule(self._event_handler, path=self._event_directory, recursive=False)
        self._observer.start()
        self._lock.start()
        self.clear()

    def stop(self):
        if self._observer is None:
            return

        self._observer.stop()
        self._observer.join()
        self._observer = None
        self._lock.stop()

    def set(self):
        with self._lock, open(self._filepath, 'a'):
            pass

    def clear(self):
        with self._lock:
            self._filepath.unlink(missing_ok=True)

    def is_set(self):
        with self._lock:
            return self._filepath.exists()

    def wait(self, timeout=None):
        return self._event_handler.wait_for_creation(timeout)


class _IpcEventFileHandler(FileSystemEventHandler):
    def __init__(self, filepath):
        self._filepath = filepath
        self._local_event = threading.Event()

    def on_created(self, event):
        if event.src_path == str(self._filepath):
            self._local_event.set()

    def on_deleted(self, event):
        if event.src_path == str(self._filepath):
            self._local_event.clear()

    def wait_for_creation(self, timeout=None):
        return self._local_event.wait(timeout)


class IpcLock:
    def __init__(self, name, lock_directory=None):
        self._name = name
        self._lock_directory = tempfile.gettempdir() if lock_directory is None else lock_directory
        unique_token = hashlib.sha256(name.encode()).hexdigest()
        self._filepath = Path(self._lock_directory, 'ipclock-' + unique_token + '.lock')

        self._event = threading.Event()
        self._event.set()

        self._event_handler = None
        self._observer = None

    def start(self):
        self._event_handler = _IpcLockFileHandler(str(self._filepath), self._event)
        self._observer = Observer()
        self._observer.schedule(self._event_handler, path=self._lock_directory, recursive=False)
        self._observer.start()
        self.release()

    def stop(self):
        if self._observer is None:
            return

        self._observer.stop()
        self._observer.join()
        self._observer = None

    def acquire(self, timeout=None):
        while True:
            if self._event.wait(timeout):
                try:
                    with open(self._filepath, 'x'):
                        self._event.clear()
                        return True
                except FileExistsError:
                    continue
            else:
                return False

    def release(self):
        self._filepath.unlink(missing_ok=True)

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.release()


class _IpcLockFileHandler(FileSystemEventHandler):
    def __init__(self, filepath, event):
        self._filepath = filepath
        self._event = event

    def on_created(self, event):
        if event.src_path == str(self._filepath):
            self._event.clear()

    def on_deleted(self, event):
        if event.src_path == str(self._filepath):
            self._event.set()
