import asyncio
import json
from threading import Thread
from modules import shared

mp_event = None
comfyui_prompt_finished_queue = None
button_event: asyncio.Event = None


# webui process
def send_request():
    global mp_event, comfyui_prompt_finished_queue
    def clear_queue(queue):
        while not queue.empty():
            queue.get()

    clear_queue(comfyui_prompt_finished_queue)
    mp_event.set()
    return comfyui_prompt_finished_queue.get()


# webui process context
def init_multiprocess_request_event(ctx):
    global mp_event, comfyui_prompt_finished_queue
    mp_event = ctx.Event()
    comfyui_prompt_finished_queue = ctx.Queue()


def release_webui_lock():
    import webui_process
    webui_process.comfyui_postprocessing_prompt_done(
        shared.last_output_images if hasattr(shared, 'last_output_images') else None)


# comfyui process
def patch_prompt_queue():
    import webui_process
    from execution import PromptQueue

    original__init__ = PromptQueue.__init__

    def patched_PromptQueue__init__(orig_self, server_self, *args, **kwargs):
        original__init__(orig_self, server_self, *args, **kwargs)

        prompt_queue = orig_self

        # task_done
        original_task_done = prompt_queue.task_done
        def patched_task_done(item_id, output, *args, **kwargs):
            if server_self.webui_locked_queue_id == item_id:
                release_webui_lock()

            original_task_done(item_id, output, *args, **kwargs)

        prompt_queue.task_done = patched_task_done

        # wipe_queue
        original_wipe_queue = prompt_queue.wipe_queue
        def patched_wipe_queue(*args, **kwargs):
            release_webui_lock()
            original_wipe_queue(*args, **kwargs)

        prompt_queue.wipe_queue = patched_wipe_queue

        # delete_queue_item
        original_delete_queue_item = prompt_queue.delete_queue_item
        def patched_delete_queue_item(function, *args, **kwargs):
            def patched_function(x):
                res = function(x)
                if res and x[0] == -server_self.webui_locked_queue_id if webui_process.fetch_comfyui_request_params()['queueFront'] else server_self.webui_locked_queue_id:
                    release_webui_lock()
                return res

            original_delete_queue_item(patched_function, *args, **kwargs)

        prompt_queue.delete_queue_item = patched_delete_queue_item

    PromptQueue.__init__ = patched_PromptQueue__init__


# webui
class RemoteComfyui:
    def queue_prompt(self, queueFront, required_node_types, images, cid):
        pass

    def get_current_workflow(self, cid):
        pass


# comfyui
class LongPollingClientHandler:
    def __init__(self):
        self.cids = set()
        self.request_times = {}

    def handle_request(self, cid):
        self.cids.add(cid)

    def handle_response(self, future_server_instance, response):
        print(response)

        if 'request' not in response:
            release_webui_lock()
            return

        if response['request'] == 'queued_prompt_comfyui':
            future_server_instance.webui_locked_queue_id = future_server_instance.number - 1

    def register_new_cid(self, cid):
        self.cids.add(cid)


# comfyui process
def patch_server_routes():
    import webui_process
    import server
    from aiohttp import web

    def init_asyncio_request_event(loop):
        global button_event
        button_event = asyncio.Event()

        def update_async_state(button_event, loop):
            while True:
                webui_process.queue_prompt_button_wait()
                loop.call_soon_threadsafe(button_event.set)

        Thread(target=update_async_state, args=(button_event, loop,)).start()

    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        init_asyncio_request_event(loop)
        original_init(self, loop, *args, **kwargs)

        self.webui_locked_queue_id = None

        comfy_client_handler = LongPollingClientHandler()

        @self.routes.post("/webui_request")
        async def webui_polling_server(request):
            global button_event
            response = await request.json()
            if 'cid' not in response:
                return web.json_response(status=400)

            comfy_client_handler.register_new_cid(response['cid'])

            comfy_client_handler.handle_response(self, response)

            await button_event.wait()
            button_event.clear()

            comfy_client_handler.handle_request(response['cid'])

            return web.json_response(webui_process.fetch_comfyui_request_params())

        @self.routes.post("/send_workflow_to_webui")
        async def send_workflow_to_webui(request):
            json_workflow = await request.json()
            workflow = json.loads(json_workflow)

            return web.json_response()

    server.PromptServer.__init__ = patched_PromptServer__init__
