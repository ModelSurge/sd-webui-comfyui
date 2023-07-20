class FinishedNotifier:
    def __init__(self, done_callback, cancelled_callback):
        self.done_cb = done_callback
        self.cancelled_cb = cancelled_callback

    def cancelled(self):
        self.cancelled_cb()

    def done(self):
        self.done_cb()


class PromptQueueTracker:
    def __init__(self, finish_notifier):
        self.notifier = finish_notifier

    def patch_original_prompt_queue(self):
        from execution import PromptQueue

        original__init__ = PromptQueue.__init__

        def patched_PromptQueue__init__(orig_self, server_self, *args, **kwargs):
            original__init__(orig_self, server_self, *args, **kwargs)

            prompt_queue = orig_self

            # task_done
            original_task_done = prompt_queue.task_done
            def patched_task_done(item_id, output, *args, **kwargs):
                with prompt_queue.mutex:
                    v = prompt_queue.currently_running[item_id]
                    if abs(v[0]) == server_self.webui_locked_queue_id:
                        # comfyui_postprocess_done()
                        self.notifier.done()

                return original_task_done(item_id, output, *args, **kwargs)

            prompt_queue.task_done = patched_task_done

            # wipe_queue
            original_wipe_queue = prompt_queue.wipe_queue
            def patched_wipe_queue(*args, **kwargs):
                with prompt_queue.mutex:
                    should_release_webui = True
                    for _, v in prompt_queue.currently_running.items():
                        if abs(v[0]) == server_self.webui_locked_queue_id:
                            should_release_webui = False

                if should_release_webui:
                    # comfyui_postprocess_cancel()
                    self.notifier.cancelled()
                return original_wipe_queue(*args, **kwargs)

            prompt_queue.wipe_queue = patched_wipe_queue

            # delete_queue_item
            original_delete_queue_item = prompt_queue.delete_queue_item
            def patched_delete_queue_item(function, *args, **kwargs):
                def patched_function(x):
                    res = function(x)
                    if res and abs(x[0]) == server_self.webui_locked_queue_id:
                        # comfyui_postprocess_cancel()
                        self.notifier.cancelled()
                    return res

                return original_delete_queue_item(patched_function, *args, **kwargs)

            prompt_queue.delete_queue_item = patched_delete_queue_item

        PromptQueue.__init__ = patched_PromptQueue__init__