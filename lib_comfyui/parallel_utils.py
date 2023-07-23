import threading
from queue import Empty

from torch import multiprocessing
import multiprocessing.queues


def clear_queue(queue: multiprocessing.Queue):
    while not queue.empty():
        try:
            queue.get(timeout=1)
        except Empty:
            pass


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


class CallbackQueue:
    def __init__(self, callback, *args, ctx=None, **kwargs):
        if ctx is None:
            ctx = multiprocessing.get_context()

        self._consumer_ready_event = multiprocessing.Event()
        self._callback = callback
        self._res_queue = multiprocessing.queues.Queue(*args, ctx=ctx, **kwargs)
        self._args_queue = multiprocessing.queues.Queue(*args, ctx=ctx, **kwargs)
        self._lock = multiprocessing.Lock()

    def attend_consumer(self, timeout: float = None):
        consumer_ready = self._wait_for_consumer(timeout)
        if not consumer_ready: return
        args, kwargs = self._args_queue.get()
        try:
            self._res_queue.put(self._callback(*args, **kwargs))
        except Exception as e:
            self._res_queue.put(RemoteError(e))

    def _wait_for_consumer(self, timeout: float = None):
        consumer_ready = self._consumer_ready_event.wait(timeout)
        self._consumer_ready_event.clear()
        return consumer_ready

    def get(self, *self_args, args=None, kwargs=None, **self_kwargs):
        self._lock.acquire()
        self._args_queue.put((args if args is not None else (), kwargs if kwargs is not None else {}))
        self._consumer_ready_event.set()
        res = self._res_queue.get(*self_args, **self_kwargs)
        self._lock.release()
        if isinstance(res, RemoteError):
            raise res.error from res
        else:
            return res


class CallbackWatcher:
    def __init__(self, queue: CallbackQueue):
        self.queue = queue
        self.producer_thread = None

    def start(self):
        def thread_loop():
            while self.producer_thread.is_running():
                self.queue.attend_consumer(timeout=1)

        self.producer_thread = StoppableThread(target=thread_loop, daemon=True)
        self.producer_thread.start()

    def stop(self):
        if self.producer_thread is None:
            return

        self.producer_thread.join()
        self.producer_thread = None


class RemoteError(Exception):
    def __init__(self, error):
        self.error = error
