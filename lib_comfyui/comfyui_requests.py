import asyncio
import json
from threading import Thread

start_comfyui_queue = None
comfyui_prompt_finished_queue = None


# webui process
def send(request_params):
    global start_comfyui_queue, comfyui_prompt_finished_queue

    # clear_queue(comfyui_prompt_finished_queue)
    start_comfyui_queue.put(request_params)
    return comfyui_prompt_finished_queue.get()


# webui process context
def init_comfyui_postprocess_request_handler(ctx):
    global start_comfyui_queue, comfyui_prompt_finished_queue
    start_comfyui_queue = ctx.Queue()
    comfyui_prompt_finished_queue = ctx.Queue()


def comfyui_postprocess_done():
    import webui_process
    images = webui_process.postprocessed_images if hasattr(webui_process, 'postprocessed_images') else None
    if images is None:
        return
    webui_process.comfyui_postprocessing_prompt_done(webui_process.postprocessed_images if hasattr(webui_process, 'postprocessed_images') else None)


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
                comfyui_postprocess_done()

            return original_task_done(item_id, output, *args, **kwargs)

        prompt_queue.task_done = patched_task_done

        # wipe_queue
        original_wipe_queue = prompt_queue.wipe_queue
        def patched_wipe_queue(*args, **kwargs):
            for _, v in server_self, prompt_queue.currently_running:
                if v[0] == server_self.webui_locked_queue_id:
                    return original_wipe_queue(*args, **kwargs)

            comfyui_postprocess_done()
            return original_wipe_queue(*args, **kwargs)

        prompt_queue.wipe_queue = patched_wipe_queue

        # delete_queue_item
        original_delete_queue_item = prompt_queue.delete_queue_item
        def patched_delete_queue_item(function, *args, **kwargs):
            def patched_function(x):
                res = function(x)
                if res and x[0] == -server_self.webui_locked_queue_id if webui_process.fetch_comfyui_postprocess_params()['queueFront'] else server_self.webui_locked_queue_id:
                    comfyui_postprocess_done()
                return res

            return original_delete_queue_item(patched_function, *args, **kwargs)

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
    def __init__(self, loop):
        self.loop = loop
        self.cids = set()
        self.client_release_event = asyncio.Event()
        self.request_params = {}

    async def halt_clients(self):
        await self.client_release_event.wait()
        self.client_release_event.clear()

    def send_request(self, params):
        self.loop.call_soon_threadsafe(self.client_release_event.set)
        self.request_params = params

    def handle_response(self, future_server_instance, response):
        print(response)

        if 'request' not in response:
            comfyui_postprocess_done()
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

    def init_requests_handler(comfy_client_handler):
        def release_long_polling_on_start_signal():
            while True:
                request_params = webui_process.comfyui_wait_for_request()
                comfy_client_handler.send_request(request_params)

        Thread(target=release_long_polling_on_start_signal).start()

    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        comfy_client_handler = LongPollingClientHandler(loop)
        init_requests_handler(comfy_client_handler)
        original_init(self, loop, *args, **kwargs)

        self.webui_locked_queue_id = None

        @self.routes.post("/webui_request")
        async def webui_polling_server(request):
            global comfyui_client_long_polling_release_event
            response = await request.json()
            if 'cid' not in response:
                return web.json_response(status=400)

            comfy_client_handler.register_new_cid(response['cid'])
            comfy_client_handler.handle_response(self, response)
            await comfy_client_handler.halt_clients()

            return web.json_response(comfy_client_handler.request_params)

        @self.routes.post("/send_workflow_to_webui")
        async def send_workflow_to_webui(request):
            json_workflow = await request.json()
            workflow = json.loads(json_workflow)

            return web.json_response()

    server.PromptServer.__init__ = patched_PromptServer__init__
