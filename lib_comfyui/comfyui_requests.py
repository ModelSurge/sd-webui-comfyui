import asyncio
import json
import time
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


# comfyui process
def patch_server_routes():
    import webui_process
    import server
    from aiohttp import web

    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        init_asyncio_request_event(loop)
        original_init(self, loop, *args, **kwargs)

        @self.routes.get("/webui_request")
        async def get_custom_route_test(request):
            global mp_event, button_event
            await button_event.wait()
            button_event.clear()
            return web.json_response(webui_process.fetch_comfyui_request_params())

        @self.routes.get("/webui_prompt_queued")
        async def webui_request_queue_prompt(request):
            def wait_for_queue_to_process_element(queue_id, and_then):
                while True:
                    server_q = self.prompt_queue.history
                    should_break = False
                    for _, v in server_q.items():
                        v_id = v['prompt'][0]
                        if v_id == queue_id:
                            should_break = True
                    if should_break:
                        break
                    time.sleep(0.5)

                and_then(shared.last_output_images if hasattr(shared, 'last_output_images') else None)

            Thread(target=wait_for_queue_to_process_element, args=(self.number-1, webui_process.comfyui_postprocessing_prompt_done)).start()
            return web.json_response()

        @self.routes.post("/send_workflow_to_webui")
        async def send_workflow_to_webui(request):
            json_workflow = await request.json()
            workflow = json.loads(json_workflow)

            return web.json_response()

    server.PromptServer.__init__ = patched_PromptServer__init__


# comfyui process
def init_asyncio_request_event(loop):
    import webui_process
    global button_event
    button_event = asyncio.Event()

    def update_async_state(button_event, loop):
        while True:
            webui_process.queue_prompt_button_wait()
            loop.call_soon_threadsafe(button_event.set)

    Thread(target=update_async_state, args=(button_event, loop, )).start()
