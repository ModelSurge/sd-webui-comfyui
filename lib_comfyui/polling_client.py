import asyncio
import atexit
import multiprocessing
import queue

from lib_comfyui.parallel_utils import clear_queue, StoppableThread
from lib_comfyui import ipc, global_state
from lib_comfyui.queue_tracker import PromptQueueTracker


# rest is ran on comfyui's server side
class ComfyuiNodeWidgetRequests:
    start_comfyui_queue = multiprocessing.Queue()
    finished_comfyui_queue = multiprocessing.Queue()
    cids = {}
    param_events = {}
    last_params = None
    loop = None
    focused_key = None

    @ipc.confine_to('comfyui')
    @staticmethod
    def send(request_params):
        clear_queue(ComfyuiNodeWidgetRequests.finished_comfyui_queue)
        ComfyuiNodeWidgetRequests.start_comfyui_queue.put(request_params)
        return ComfyuiNodeWidgetRequests.finished_comfyui_queue.get()

    @ipc.confine_to('comfyui')
    @staticmethod
    def start_workflow_sync(batch, workflow_type, is_img2img, required_node_types, queue_front):
        xxx2img = ("img2img" if is_img2img else "txt2img")
        setattr(global_state, f'{xxx2img}_{workflow_type}_input_images', batch)
        setattr(global_state, f'tab_name', xxx2img)
        PromptQueueTracker.update_tracked_id()
        response = ComfyuiNodeWidgetRequests.send({
            'request': '/sd-webui-comfyui/webui_request_queue_prompt',
            'workflowType': f'comfyui_{workflow_type}_{xxx2img}',
            'requiredNodeTypes': required_node_types,
            'queueFront': queue_front,
        })

        if 'error' in response:
            return response

        # unsafe queue tracking
        PromptQueueTracker.wait_for_last_put()

        output_key = f'{xxx2img}_{workflow_type}_output_images'
        results = getattr(global_state, output_key, None)
        delattr(global_state, output_key)

        return results

    @classmethod
    def set_loop(cls, loop):
        if loop is None or cls.loop is not None:
            return

        cls.loop = loop
        cls._start_listener()

    @classmethod
    def _start_listener(cls):
        def request_listener():
            nonlocal request_thread
            while request_thread.is_running():
                try:
                    cls.last_params = cls.start_comfyui_queue.get(timeout=1)
                except queue.Empty:
                    continue
                key = ComfyuiNodeWidgetRequests.focused_key
                cls.loop.call_soon_threadsafe(cls.param_events[key][cls.last_params['workflowType']].set)

        request_thread = StoppableThread(target=request_listener)
        request_thread.start()
        atexit.register(request_thread.join)

    @classmethod
    def add_client(cls, cid, key):
        if key not in cls.cids.keys():
            cls.cids[key] = set()
        if key not in cls.param_events.keys():
            cls.param_events[key] = {}
        if cid in cls.cids[key]:
            return

        # REMOVE THIS AT SOME POINT
        ComfyuiNodeWidgetRequests.focused_key = key

        cls.param_events[key][cid] = asyncio.Event()
        cls.cids[key].add(cid)
        print(f'[sd-webui-comfyui] registered new ComfyUI client - {cid}')

    @classmethod
    async def handle_response(cls, response):
        cls.finished_comfyui_queue.put(response)

    @classmethod
    async def handle_request(cls, cid, key):
        await cls.param_events[key][cid].wait()
        cls.param_events[key][cid].clear()
        return cls.last_params


def polling_server_patch(instance, loop):
    from aiohttp import web

    ComfyuiNodeWidgetRequests.set_loop(loop)

    @instance.routes.post("/sd-webui-comfyui/webui_polling_server")
    async def webui_polling_server(request):
        response = await request.json()
        if 'key' not in response:
            return web.json_response(status=400)
        if 'cid' not in response:
            return web.json_response(status=400)

        key = response['key']
        cid = response['cid']

        if not (key in ComfyuiNodeWidgetRequests.cids.keys() and cid in ComfyuiNodeWidgetRequests.cids[key]):
            ComfyuiNodeWidgetRequests.add_client(cid, key)
        else:
            if 'error' in response:
                print(f"[sd-webui-comfyui] Client {cid}-{key} encountered an error - \n{response['error']}")
            await ComfyuiNodeWidgetRequests.handle_response(response)

        request = await ComfyuiNodeWidgetRequests.handle_request(cid, key)
        print(f'[sd-webui-comfyui] send request - \n{request}')
        return web.json_response(request)

    @instance.routes.post("/sd-webui-comfyui/set_polling_server_focused_key")
    async def set_polling_server_focused_key(request):
        request_json = await request.json()
        if 'key' not in request_json:
            return web.json_response(status=400)

        key = request_json['key']
        ComfyuiNodeWidgetRequests.focused_key = key
        print(f'[sd-webui-comfyui] set client key - \n{key}')
        return web.json_response()


def add_server__init__patch(cb):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        original_init(self, loop, *args, **kwargs)
        cb(self, loop, *args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__


def patch_server_routes():
    add_server__init__patch(polling_server_patch)
