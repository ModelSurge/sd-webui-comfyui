import functools
import multiprocessing
from lib_comfyui import ipc


class PromptQueueTracker:
    done_event = multiprocessing.Event()
    put_event = multiprocessing.Event()
    tracked_id = None
    original_id = None
    queue_instance = None
    server_instance = None

    @staticmethod
    def patched__init__(self, server_instance):
        prompt_queue = self
        PromptQueueTracker.server_instance = server_instance
        PromptQueueTracker.queue_instance = self

        def patched_put(item, *args, original_put, **kwargs):
            with prompt_queue.mutex:
                if abs(item[0]) == PromptQueueTracker.tracked_id:
                    PromptQueueTracker.put_event.set()

                return original_put(item, *args, **kwargs)

        prompt_queue.put = functools.partial(patched_put, original_put=prompt_queue.put)

        # task_done
        def patched_task_done(item_id, output, *args, original_task_done, **kwargs):
            with prompt_queue.mutex:
                v = prompt_queue.currently_running[item_id]
                if abs(v[0]) == PromptQueueTracker.tracked_id:
                    PromptQueueTracker.done_event.set()

                return original_task_done(item_id, output, *args, **kwargs)

        prompt_queue.task_done = functools.partial(patched_task_done, original_task_done=prompt_queue.task_done)

        # wipe_queue
        def patched_wipe_queue(*args, original_wipe_queue, **kwargs):
            with prompt_queue.mutex:
                should_release_webui = True
                for _, v in prompt_queue.currently_running.items():
                    if abs(v[0]) == PromptQueueTracker.tracked_id:
                        should_release_webui = False

                if should_release_webui:
                    PromptQueueTracker.done_event.set()

                return original_wipe_queue(*args, **kwargs)

        prompt_queue.wipe_queue = functools.partial(patched_wipe_queue, original_wipe_queue=prompt_queue.wipe_queue)

        # delete_queue_item
        def patched_delete_queue_item(function, *args, original_delete_queue_item, **kwargs):
            def patched_function(x):
                res = function(x)
                if res and abs(x[0]) == PromptQueueTracker.tracked_id:
                    PromptQueueTracker.done_event.set()
                return res

            return original_delete_queue_item(patched_function, *args, **kwargs)

        prompt_queue.delete_queue_item = functools.partial(patched_delete_queue_item, original_delete_queue_item=prompt_queue.delete_queue_item)


@ipc.restrict_to_process('comfyui')
def setup_tracker_id():
    PromptQueueTracker.original_id = PromptQueueTracker.tracked_id
    PromptQueueTracker.tracked_id = PromptQueueTracker.server_instance.number
    PromptQueueTracker.put_event.clear()
    PromptQueueTracker.done_event.clear()


@ipc.restrict_to_process('comfyui')
def wait_until_done():
    was_put = PromptQueueTracker.put_event.wait(timeout=3)
    if not was_put:
        PromptQueueTracker.tracked_id = PromptQueueTracker.original_id
        return

    if not tracked_id_present():
        return

    while True:
        has_been_set = PromptQueueTracker.done_event.wait(timeout=1)
        if has_been_set:
            return


@ipc.restrict_to_process('comfyui')
def tracked_id_present():
    with PromptQueueTracker.queue_instance.mutex:
        for v in PromptQueueTracker.queue_instance.currently_running.values():
            if abs(v[0]) == PromptQueueTracker.tracked_id:
                return True
        for x in PromptQueueTracker.queue_instance.queue:
            if abs(x[0]) == PromptQueueTracker.tracked_id:
                return True
        return False


@ipc.restrict_to_process('comfyui')
def add_queue__init__patch(callback):
    import execution
    original_init = execution.PromptQueue.__init__

    def patched_PromptQueue__init__(self, server, *args, **kwargs):
        original_init(self, server, *args, **kwargs)
        callback(self, server, *args, **kwargs)

    execution.PromptQueue.__init__ = patched_PromptQueue__init__


@ipc.restrict_to_process('comfyui')
def patch_prompt_queue():
    add_queue__init__patch(PromptQueueTracker.patched__init__)
