import threading
from torch import multiprocessing
import multiprocessing.queues


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

    def attend_consumer(self, timeout: float = None):
        consumer_ready = self._wait_for_consumer(timeout)
        if not consumer_ready: return
        self.put(self._producer())

    def _wait_for_consumer(self, timeout: float = None):
        consumer_ready = self._consumer_ready_event.wait(timeout)
        self._consumer_ready_event.clear()
        return consumer_ready

    def get(self, *args, **kwargs):
        self._consumer_ready_event.set()
        return super(SynchronizingQueue, self).get(*args, **kwargs)

    def __getstate__(self):
        return super(SynchronizingQueue, self).__getstate__() + (self._consumer_ready_event, self._producer)

    def __setstate__(self, state):
        *state, self._consumer_ready_event, self._producer = state
        return super(SynchronizingQueue, self).__setstate__(state)
