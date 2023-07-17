import asyncio
from threading import Thread

mp_event = None
button_event: asyncio.Event = None


def send_request():
    global mp_event
    mp_event.set()


def init_multiprocess_button_event(ctx):
    global mp_event
    mp_event = ctx.Event()


def patch_server_routes():
    import server
    from aiohttp import web

    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        init_asyncio_button_event(loop)
        original_init(self, loop, *args, **kwargs)

        @self.routes.get("/request_press_queue_prompt_button")
        async def get_custom_route_test(request):
            global mp_event, button_event
            await button_event.wait()
            button_event.clear()
            return web.json_response({'promptQueue': True, 'batchSize': 1})

    server.PromptServer.__init__ = patched_PromptServer__init__


def init_asyncio_button_event(loop):
    import webui_process
    global button_event
    button_event = asyncio.Event()

    def update_async_state(button_event, loop):
        while True:
            webui_process.queue_prompt_button_wait()
            loop.call_soon_threadsafe(button_event.set)

    Thread(target=update_async_state, args=(button_event, loop, )).start()
