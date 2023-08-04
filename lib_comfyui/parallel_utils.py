import threading
from queue import Empty
from torch import multiprocessing
import multiprocessing.queues
from lib_comfyui import platform_utils


def clear_queue(queue: multiprocessing.Queue):
    while not queue.empty():
        try:
            queue.get(timeout=1)
        except Empty:
            pass


class StoppableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def join(self, *args, **kwargs) -> None:
        self.stop()
        super().join(*args, **kwargs)

    def is_running(self):
        return not self.stop_event.is_set()


class CallbackQueue:
    def __init__(self, callback, *args, ctx=None, **kwargs):
        if ctx is None:
            ctx = multiprocessing.get_context()

        if platform_utils.is_windows():
            self.consumer_ready_event = multiprocessing.Event()
            self.callback = callback
            self.res_queue = multiprocessing.queues.Queue(*args, ctx=ctx, **kwargs)
            self.args_queue = multiprocessing.queues.Queue(*args, ctx=ctx, **kwargs)
            self.lock = multiprocessing.Lock()
        else:
            manager = ctx.Manager()
            self.consumer_ready_event = manager.Event()
            self.callback = callback
            self.res_queue = manager.Queue(*args, **kwargs)
            self.args_queue = manager.Queue(*args, **kwargs)
            self.lock = manager.Lock()

    def attend_consumer(self, timeout: float = None):
        consumer_ready = self.wait_for_consumer(timeout)
        if not consumer_ready: return
        args, kwargs = self.args_queue.get()
        try:
            self.res_queue.put(self.callback(*args, **kwargs))
        except Exception as e:
            self.res_queue.put(RemoteError(e))

    def wait_for_consumer(self, timeout: float = None):
        consumer_ready = self.consumer_ready_event.wait(timeout)
        if consumer_ready:
            self.consumer_ready_event.clear()

        return consumer_ready

    def get(self, *self_args, args=None, kwargs=None, **self_kwargs):
        self.lock.acquire()
        self.args_queue.put((args if args is not None else (), kwargs if kwargs is not None else {}))
        self.consumer_ready_event.set()
        res = self.res_queue.get(*self_args, **self_kwargs)
        self.lock.release()
        if isinstance(res, RemoteError):
            raise res.error from res
        else:
            return res

    def __getstate__(self):
        return (
            self.consumer_ready_event,
            self.callback,
            self.res_queue,
            self.args_queue,
            self.lock,
        )

    def __setstate__(self, state):
        (
            self.consumer_ready_event,
            self.callback,
            self.res_queue,
            self.args_queue,
            self.lock,
        ) = state


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

    def is_running(self):
        return self.producer_thread and self.producer_thread.is_running()

    def stop(self):
        if self.producer_thread is None:
            return

        self.producer_thread.join()
        self.producer_thread = None


class RemoteError(Exception):
    def __init__(self, error):
        self.error = error
