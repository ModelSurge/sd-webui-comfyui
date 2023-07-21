import functools
import multiprocessing
from lib_comfyui import ipc


class PromptQueueTracker:
    done_event = multiprocessing.Event()
    tracked_id = None
    queue_instance = None
    server_instance = None

    @ipc.confine_to('comfyui')
    @staticmethod
    def wait_for_last_put():
        if not PromptQueueTracker.tracked_id_present():
            return

        PromptQueueTracker.done_event.wait()
        PromptQueueTracker.done_event.clear()

    @ipc.confine_to('comfyui')
    @staticmethod
    def tracked_id_present():
        with PromptQueueTracker.queue_instance.mutex:
            for v in PromptQueueTracker.queue_instance.currently_running.values():
                if abs(v[0]) == PromptQueueTracker.tracked_id:
                    return True
            for x in PromptQueueTracker.queue_instance.queue:
                if abs(x[0]) == PromptQueueTracker.tracked_id:
                    return True
            return False


    @ipc.confine_to('comfyui')
    @staticmethod
    def update_tracked_id():
        PromptQueueTracker.tracked_id = PromptQueueTracker.server_instance.number

    @staticmethod
    def patched__init__(self, server_instance):
        prompt_queue = self
        PromptQueueTracker.server_instance = server_instance
        PromptQueueTracker.queue_instance = self

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


def add_queue__init__patch(callback):
    import execution
    original_init = execution.PromptQueue.__init__

    def patched_PromptQueue__init__(self, server, *args, **kwargs):
        original_init(self, server, *args, **kwargs)
        callback(self, server, *args, **kwargs)

    execution.PromptQueue.__init__ = patched_PromptQueue__init__


def patch_prompt_queue():
    add_queue__init__patch(PromptQueueTracker.patched__init__)