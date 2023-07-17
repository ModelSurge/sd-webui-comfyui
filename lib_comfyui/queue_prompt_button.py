import asyncio
from threading import Thread

mp_event = None
button_event: asyncio.Event = None

# webui process
def send_request():
    global mp_event
    mp_event.set()


# webui process context
def init_multiprocess_button_event(ctx):
    global mp_event
    mp_event = ctx.Event()


# comfyui process
def patch_server_routes():
    import webui_process
    import server
    from aiohttp import web

    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        init_asyncio_button_event(loop)
        original_init(self, loop, *args, **kwargs)

        @self.routes.get("/webui_request_queue_prompt")
        async def get_custom_route_test(request):
            global mp_event, button_event
            await button_event.wait()
            button_event.clear()
            return web.json_response(webui_process.fetch_queue_prompt_params())

    server.PromptServer.__init__ = patched_PromptServer__init__


# comfyui process
def init_asyncio_button_event(loop):
    import webui_process
    global button_event
    button_event = asyncio.Event()

    def update_async_state(button_event, loop):
        while True:
            webui_process.queue_prompt_button_wait()
            loop.call_soon_threadsafe(button_event.set)

    Thread(target=update_async_state, args=(button_event, loop, )).start()
