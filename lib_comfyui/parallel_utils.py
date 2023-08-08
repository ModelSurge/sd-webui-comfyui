import hashlib
import multiprocessing.shared_memory
import os
import pickle
import tempfile
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

if os.name == 'posix':
    import multiprocessing.resource_tracker as mp_resource_tracker
else:
    mp_resource_tracker = None


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

        self._res_sender.start()
        self._args_receiver.start()
        self._producer_thread = StoppableThread(target=thread_loop, daemon=True)
        self._producer_thread.start()

    def stop(self):
        if self._producer_thread is None:
            return

        self._producer_thread.join()
        self._producer_thread = None
        self._args_receiver.stop()
        self._res_sender.stop()

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
        self.start()

    def start(self):
        self._res_receiver.start()
        self._args_sender.start()

    def stop(self):
        self._args_sender.stop()
        self._res_receiver.stop()

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
    def __init__(self, name):
        self._name = name
        self._shm = None
        self._memory_free_event = IpcEvent(f"memory_free_{name}")
        self._send_event = IpcEvent(f"send_{name}", on_set_callbacks=[self.close_shm])
        self._recv_event = IpcEvent(f"recv_{name}", on_set_callbacks=[self._memory_free_event.clear])
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self._send_event.start()
        self._recv_event.start()
        self._memory_free_event.start()

        self._send_event.set()
        self._recv_event.clear()
        self._memory_free_event.set()

    def stop(self):
        self._recv_event.stop()
        self._send_event.stop()
        self.close_shm()
        self._memory_free_event.stop()

    def close_shm(self):
        if self._shm:
            self._shm.close()
            self._shm.unlink()
            self._shm = None
            logging.warning('IPC payload %s\tfree memory', self._name)
        self._memory_free_event.set()

    def send(self, value: Any, timeout: Optional[float] = None):
        is_ready = self._send_event.wait(timeout=timeout)
        if not is_ready:
            raise TimeoutError

        logging.warning('IPC payload %s\tsend value: %s', self._name, str(value))
        data = pickle.dumps(value)

        self._memory_free_event.wait()
        try:
            self._shm = multiprocessing.shared_memory.SharedMemory(f"sd_webui_comfyui_ipc_shm_{self._name}")
            self._shm.close()
            self._shm.unlink()
        except FileNotFoundError:
            pass

        self._shm = multiprocessing.shared_memory.SharedMemory(f"sd_webui_comfyui_ipc_shm_{self._name}", create=True, size=len(data))
        self._shm.buf[:] = data

        self._send_event.clear()
        self._recv_event.set()


class IpcReceiver:
    def __init__(self, name):
        self._name = name
        self._send_event = IpcEvent(f"send_{name}")
        self._recv_event = IpcEvent(f"recv_{name}")
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self._send_event.start()
        self._recv_event.start()
        self._send_event.set()
        self._recv_event.clear()

    def stop(self):
        self._recv_event.stop()
        self._send_event.stop()

    def recv(self, timeout: Optional[float] = None) -> Any:
        is_ready = self._recv_event.wait(timeout=timeout)
        if not is_ready:
            raise TimeoutError

        shm = multiprocessing.shared_memory.SharedMemory(f"sd_webui_comfyui_ipc_shm_{self._name}")

        with RestoreTorchLoad():
            value = pickle.loads(shm.buf)

        logging.warning('IPC payload %s\treceive value: %s', self._name, str(value))
        shm.close()

        self._recv_event.clear()
        self._send_event.set()

        return value


def close_shm(shm):
    if shm:
        shm.close()
        try:
            shm.unlink()
        except FileNotFoundError:
            pass

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
    def __init__(self, name, event_directory=None, on_set_callbacks=None):
        self._name = name
        self._event_directory = tempfile.gettempdir() if event_directory is None else event_directory
        unique_token = hashlib.sha256(name.encode()).hexdigest()
        self._event_path = Path(self._event_directory, 'ipcevent-' + unique_token + '.event')
        self._alive_path = Path(self._event_directory, 'ipclock-alive-' + unique_token + '.lifetime')
        self._alive_file = None

        self._event = threading.Event()
        self._observer = None
        self._on_set_callbacks = on_set_callbacks if on_set_callbacks else []

        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        if self._alive_file is not None:
            return

        self._event.clear()
        event_handler = _IpcEventFileHandler(str(self._event_path), self._event, self._on_set_callbacks)
        self._observer = Observer()
        self._observer.schedule(event_handler, path=self._event_directory, recursive=False)
        self._observer.start()

        try:
            with open(self._alive_path, 'x'): pass
            logging.warning('detected stale event file %s %s', str(self._alive_path), self._name)
            self._event_path.unlink(missing_ok=True)
            self._alive_file = open(self._alive_path, 'a')
        except FileExistsError:
            logging.warning('event file is not stale, opening file %s %s', str(self._alive_path), self._name)
            self._alive_file = open(self._alive_path, 'a')
            if self._event_path.exists():
                self._event.set()
        except FileNotFoundError:
            logging.warning('event file not found, creating it %s %s', str(self._alive_path), self._name)
            self._event_path.unlink(missing_ok=True)
            with open(self._alive_path, 'x'): pass
            self._alive_file = open(self._alive_path, 'a')

    def stop(self):
        if self._alive_file is not None:
            self._alive_file.close()
            self._alive_file = None

        try:
            self._alive_path.unlink(missing_ok=True)
        except PermissionError:
            pass

        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def set(self):
        with open(self._event_path, 'a'):
            pass

    def clear(self):
        while True:
            try:
                self._event_path.unlink(missing_ok=True)
                break
            except PermissionError:
                time.sleep(0.01)  # reduces the number of retries drastically (~100 -> ~1)
                continue

    def is_set(self):
        return self._event_path.exists()

    def wait(self, timeout=None):
        res = self._event.wait(timeout)
        return res


class _IpcEventFileHandler(FileSystemEventHandler):
    def __init__(self, filepath, event, on_set_callbacks):
        self._filepath = filepath
        self._event = event
        self._on_set_callbacks = on_set_callbacks

    def on_created(self, event):
        if event.src_path == str(self._filepath):
            for callback in self._on_set_callbacks:
                callback()
            self._event.set()

    def on_deleted(self, event):
        if event.src_path == str(self._filepath):
            self._event.clear()
