import threading
from lib_comfyui import ipc_payload


class CallbackWatcher:
    def __init__(self, callback, name: str, strategy_factory):
        self._callback = callback
        self._res_sender = ipc_payload.IpcSender(f'res_{name}', strategy_factory)
        self._args_receiver = ipc_payload.IpcReceiver(f'args_{name}', strategy_factory)
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
    def __init__(self, name: str, strategy_factory):
        self._res_receiver = ipc_payload.IpcReceiver(f'res_{name}', strategy_factory)
        self._args_sender = ipc_payload.IpcSender(f'args_{name}', strategy_factory)

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

