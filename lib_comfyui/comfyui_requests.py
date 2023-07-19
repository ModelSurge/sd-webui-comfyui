import asyncio
import json
from threading import Thread
from lib_comfyui.parallel_utils import clear_queue

start_comfyui_queue = None
comfyui_prompt_finished_queue = None


# webui
def send(request_params):
    global start_comfyui_queue, comfyui_prompt_finished_queue

    clear_queue(comfyui_prompt_finished_queue)

    start_comfyui_queue.put(request_params)
    return comfyui_prompt_finished_queue.get()


# webui
def init_comfyui_postprocess_request_handler(ctx):
    global start_comfyui_queue, comfyui_prompt_finished_queue
    start_comfyui_queue = ctx.Queue()
    comfyui_prompt_finished_queue = ctx.Queue()


# comfyui
def comfyui_postprocess_done():
    import webui_process
    images = webui_process.postprocessed_images if hasattr(webui_process, 'postprocessed_images') else None
    webui_process.comfyui_postprocessing_prompt_done(images)


# comfyui
def comfyui_postprocess_cancel():
    import webui_process
    webui_process.comfyui_postprocessing_prompt_done(None)


# comfyui
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
        comfy_client_handler = LongPollingComfyuiClient(loop)
        init_requests_handler(comfy_client_handler)
        original_init(self, loop, *args, **kwargs)

        self.webui_locked_queue_id = None

        @self.routes.post("/sd-webui-comfyui/webui_request")
        async def webui_polling_server(request):
            global comfyui_client_long_polling_release_event
            response = await request.json()
            if 'cid' not in response:
                return web.json_response(status=400)

            comfy_client_handler.handle_response(self, response)
            await comfy_client_handler.halt_clients_until_request(response)

            return web.json_response(comfy_client_handler.get_request_params(response))

        @self.routes.post("/sd-webui-comfyui/send_workflow_to_webui")
        async def send_workflow_to_webui(request):
            json_workflow = await request.json()
            workflow = json.loads(json_workflow)

            return web.json_response()

    server.PromptServer.__init__ = patched_PromptServer__init__


# comfyui
class LongPollingComfyuiClient:
    def __init__(self, loop):
        self.loop = loop
        self.cids = set()
        self.client_release_event = asyncio.Event()
        self.request_params = {}

    def send_request(self, params):
        self.request_params = params
        self.loop.call_soon_threadsafe(self.client_release_event.set)

    def handle_response(self, future_server_instance, response):
        if 'request' not in response:
            return

        if response['request'] == 'register_cid':
            self.register_new_cid(response['cid'])
            print(f'[sd-webui-comfyui] registered new ComfyUI client - {response["cid"]}')
        if response['cid'] not in self.cids:
            return

        if response['request'] == 'queued_prompt_comfyui':
            future_server_instance.webui_locked_queue_id = future_server_instance.number - 1
            future_server_instance.request_params = self.request_params
            print(f'[sd-webui-comfyui] queued prompt - {response["cid"]}')
            return

    async def halt_clients_until_request(self, response):
        if response['cid'] not in self.cids:
            return

        await self.client_release_event.wait()
        self.client_release_event.clear()

    def register_new_cid(self, cid):
        self.cids.add(cid)

    def get_request_params(self, response):
        if response['cid'] not in self.cids:
            return {
                'access': 'denied'
            }
        return self.request_params


# comfyui
def patch_prompt_queue():
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
                    comfyui_postprocess_done()

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
                comfyui_postprocess_cancel()
            return original_wipe_queue(*args, **kwargs)

        prompt_queue.wipe_queue = patched_wipe_queue

        # delete_queue_item
        original_delete_queue_item = prompt_queue.delete_queue_item
        def patched_delete_queue_item(function, *args, **kwargs):
            def patched_function(x):
                res = function(x)
                if res and abs(x[0]) == server_self.webui_locked_queue_id:
                    comfyui_postprocess_cancel()
                return res

            return original_delete_queue_item(patched_function, *args, **kwargs)

        prompt_queue.delete_queue_item = patched_delete_queue_item

    PromptQueue.__init__ = patched_PromptQueue__init__