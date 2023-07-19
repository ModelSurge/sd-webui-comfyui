import importlib
import sys
import threading
from torch import multiprocessing
import multiprocessing.queues


def confine_to(process_id):
    def annotation(function):
        def wrapper(*args, **kwargs):
            global current_process_id
            if process_id == current_process_id:
                return function(*args, **kwargs)
            else:
                return process_queues[process_id].get(args=(function.__module__, function.__qualname__, args, kwargs))

        return wrapper

    return annotation


class StoppableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def join(self, *args, **kwargs) -> None:
        self.stop()
        super(StoppableThread, self).join(*args, **kwargs)

    def is_running(self):
        return not self._stop_event.is_set()


class SynchronizingQueue(multiprocessing.queues.Queue):
    def __init__(self, callback, *args, ctx=None, **kwargs):
        if ctx is None:
            ctx = multiprocessing.get_context()

        super(SynchronizingQueue, self).__init__(*args, ctx=ctx, **kwargs)
        self._consumer_ready_event = multiprocessing.Event()
        self._callback = callback
        self._args_queue = multiprocessing.queues.Queue(*args, ctx=ctx, **kwargs)
        self._lock = multiprocessing.Lock()

    def attend_consumer(self, timeout: float = None):
        consumer_ready = self._wait_for_consumer(timeout)
        if not consumer_ready: return
        args, kwargs = self._args_queue.get()
        try:
            self.put(self._callback(*args, **kwargs))
        except Exception as e:
            self.put(RemoteError(e))

    def _wait_for_consumer(self, timeout: float = None):
        consumer_ready = self._consumer_ready_event.wait(timeout)
        self._consumer_ready_event.clear()
        return consumer_ready

    def get(self, *base_args, args=None, kwargs=None, **base_kwargs):
        self._lock.acquire()
        self._args_queue.put((args if args is not None else (), kwargs if kwargs is not None else {}))
        self._consumer_ready_event.set()
        res = super(SynchronizingQueue, self).get(*base_args, **base_kwargs)
        self._lock.release()
        if isinstance(res, RemoteError):
            raise res.error from res
        else:
            return res

    def __getstate__(self):
        return super(SynchronizingQueue, self).__getstate__() + (self._consumer_ready_event, self._callback, self._args_queue, self._lock)

    def __setstate__(self, state):
        *state, self._consumer_ready_event, self._callback, self._args_queue, self._lock = state
        return super(SynchronizingQueue, self).__setstate__(state)


class ProducerHandler:
    def __init__(self, queue: SynchronizingQueue):
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


def call_fully_qualified(module_name, qualified_name, args, kwargs):
    module_parts = module_name.split('.')
    try:
        module = sys.modules[module_name.split('.')[0]]
        for part in module_parts[1:]:
            module = getattr(module_parts, part)
    except:
        source_module = module_parts[-1]
        module = importlib.import_module(module_name, source_module)

    function = module
    for name in qualified_name.split('.'):
        function = getattr(function, name)
    return function(*args, **kwargs)


current_process_id = 'webui'
process_callback_listeners = {
    'webui': ProducerHandler(SynchronizingQueue(call_fully_qualified)),
}
process_queues = {}


def get_process_queues():
    return {k: v.queue for k, v in process_callback_listeners.items()}


def start_process_queues():
    for callback_listener in process_callback_listeners.values():
        callback_listener.start()


def stop_process_queues():
    for callback_listener in process_callback_listeners.values():
        callback_listener.stop()
