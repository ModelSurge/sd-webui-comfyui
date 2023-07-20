import asyncio
import multiprocessing
from threading import Thread
from lib_comfyui.parallel_utils import clear_queue


# webui pass-through
class WebuiNodeWidgetRequests:
    start_comfyui_queue = None
    finished_comfyui_queue = None

    @classmethod
    def init(cls, ctx):
        cls.start_comfyui_queue = ctx.Queue()
        cls.finished_comfyui_queue = ctx.Queue()

    @classmethod
    def send(cls, request_params):
        clear_queue(cls.finished_comfyui_queue)
        cls.start_comfyui_queue.put(request_params)
        cls.finished_comfyui_queue.get()

    @classmethod
    def get_queues(cls):
        return cls.start_comfyui_queue, cls.finished_comfyui_queue


# rest is ran on comfyui's server side
class ComfyuiNodeWidgetRequests:
    start_comfyui_queue = None
    finished_comfyui_queue = None
    cids = set()
    param_events = {}
    last_params = None
    loop = None

    @classmethod
    def init(cls, start_q: multiprocessing.Queue, end_q: multiprocessing.Queue):
        cls.start_comfyui_queue = start_q
        cls.finished_comfyui_queue = end_q

    @classmethod
    def set_loop(cls, loop):
        cls.loop = loop

    @classmethod
    def start_listener(cls):
        def request_listener():
            while True:
                cls.last_params = cls.start_comfyui_queue.get()
                cls.loop.call_soon_threadsafe(cls.param_events[cls.last_params['workflowType']].set)

        Thread(target=request_listener).start()

    @classmethod
    def add_client(cls, cid):
        if cid in cls.cids:
            return

        cls.cids.add(cid)
        cls.param_events[cid] = asyncio.Event()
        print(f'[sd-webui-comfyui] registered new ComfyUI client - {cid}')

    @classmethod
    async def handle_response(cls, response):
        cls.finished_comfyui_queue.put(response)

    @classmethod
    async def handle_request(cls, cid):
        await cls.param_events[cid].wait()
        cls.param_events[cid].clear()
        return cls.last_params


def polling_server_patch(instance, loop):
    from aiohttp import web

    ComfyuiNodeWidgetRequests.set_loop(loop)

    @instance.routes.post("/sd-webui-comfyui/webui_polling_server")
    async def webui_polling_server(request):
        response = await request.json()
        if 'cid' not in response:
            return web.json_response(status=400)

        cid = response['cid']

        if cid not in ComfyuiNodeWidgetRequests.cids:
            ComfyuiNodeWidgetRequests.add_client(cid)
        else:
            if 'error' in response:
                print(f"[sd-webui-comfyui] Client {cid} encountered an error - \n{response['error']}")
            await ComfyuiNodeWidgetRequests.handle_response(response)

        request = await ComfyuiNodeWidgetRequests.handle_request(cid)
        print(f'[sd-webui-comfyui] send request - \n{request}')
        return web.json_response(request)


def add_server__init__patch(cb):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        original_init(self, loop, *args, **kwargs)
        cb(self, loop, *args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__


def patch_server_routes():
    add_server__init__patch(polling_server_patch)
