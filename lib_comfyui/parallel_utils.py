import threading
from torch import multiprocessing
import multiprocessing.queues
import traceback


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
    def __init__(self, producer, *args, ctx=None, **kwargs):
        if ctx is None:
            ctx = multiprocessing.get_context()

        super(SynchronizingQueue, self).__init__(*args, ctx=ctx, **kwargs)
        self._consumer_ready_event = multiprocessing.Event()
        self._producer = producer
        self._args_stack = multiprocessing.queues.Queue(*args, ctx=ctx, **kwargs)

    def attend_consumer(self, timeout: float = None):
        consumer_ready = self._wait_for_consumer(timeout)
        if not consumer_ready: return
        args, kwargs = self._args_stack.get()
        try:
            self.put(self._producer(*args, **kwargs))
        except Exception as e:
            traceback.print_exc()
            self.put(e)

    def _wait_for_consumer(self, timeout: float = None):
        consumer_ready = self._consumer_ready_event.wait(timeout)
        self._consumer_ready_event.clear()
        return consumer_ready

    def get(self, *base_args, args=None, kwargs=None, **base_kwargs):
        self._args_stack.put((args if args is not None else (), kwargs if kwargs is not None else {}))
        self._consumer_ready_event.set()
        res = super(SynchronizingQueue, self).get(*base_args, **base_kwargs)
        if isinstance(res, Exception): raise res
        else: return res

    def __getstate__(self):
        return super(SynchronizingQueue, self).__getstate__() + (self._consumer_ready_event, self._producer, self._args_stack)

    def __setstate__(self, state):
        *state, self._consumer_ready_event, self._producer, self._args_stack = state
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
