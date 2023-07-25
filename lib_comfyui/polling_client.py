import asyncio
import multiprocessing

from lib_comfyui.parallel_utils import clear_queue, StoppableThread
from lib_comfyui import ipc, global_state
from lib_comfyui.queue_tracker import PromptQueueTracker


# rest is ran on comfyui's server side
class ComfyuiNodeWidgetRequests:
    start_comfyui_queue = multiprocessing.Queue()
    finished_comfyui_queue = multiprocessing.Queue()
    comfyui_iframe_ids = {}
    param_events = {}
    last_params = None
    loop = None
    focused_webui_client_id = None

    @ipc.confine_to('comfyui')
    @staticmethod
    def send(request_params):
        cls = ComfyuiNodeWidgetRequests
        if cls.focused_webui_client_id is None:
            return None
        clear_queue(cls.finished_comfyui_queue)
        webui_client_id = cls.focused_webui_client_id
        cls.last_params = request_params
        cls.loop.call_soon_threadsafe(cls.param_events[webui_client_id][cls.last_params['workflowType']].set)
        result = cls.finished_comfyui_queue.get(timeout=10)

        return result

    @ipc.confine_to('comfyui')
    @staticmethod
    def start_workflow_sync(batch, workflow_type, is_img2img, required_node_types, queue_front):
        xxx2img = ("img2img" if is_img2img else "txt2img")
        output_key = f'{xxx2img}_{workflow_type}_output_images'
        input_key = f'{xxx2img}_{workflow_type}_input_images'
        setattr(global_state, input_key, batch)
        setattr(global_state, f'tab_name', xxx2img)
        if output_key in global_state:
            delattr(global_state, output_key)

        PromptQueueTracker.setup_tracker_id()

        # unsafe queue tracking
        response = ComfyuiNodeWidgetRequests.send({
            'request': '/sd-webui-comfyui/webui_request_queue_prompt',
            'workflowType': f'comfyui_{workflow_type}_{xxx2img}',
            'requiredNodeTypes': required_node_types,
            'queueFront': queue_front,
        })

        if response is None or 'error' in response:
            return response

        PromptQueueTracker.wait_until_done()

        results = getattr(global_state, output_key, [])

        return results

    @classmethod
    def init_request_listener(cls, loop):
        if loop is None or cls.loop is not None:
            return

        cls.loop = loop

    @classmethod
    def add_client(cls, comfyui_iframe_id, webui_client_id):
        if webui_client_id not in cls.comfyui_iframe_ids:
            cls.comfyui_iframe_ids[webui_client_id] = set()
        if webui_client_id not in cls.param_events:
            cls.param_events[webui_client_id] = {}
        if comfyui_iframe_id in cls.comfyui_iframe_ids[webui_client_id]:
            return

        # REMOVE THIS AT SOME POINT
        ComfyuiNodeWidgetRequests.focused_webui_client_id = webui_client_id

        cls.param_events[webui_client_id][comfyui_iframe_id] = asyncio.Event()
        cls.comfyui_iframe_ids[webui_client_id].add(comfyui_iframe_id)
        print(f'[sd-webui-comfyui] registered new ComfyUI client - {comfyui_iframe_id}')

    @classmethod
    async def handle_response(cls, response):
        cls.finished_comfyui_queue.put(response)

    @classmethod
    async def handle_request(cls, comfyui_iframe_id, webui_client_id):
        await cls.param_events[webui_client_id][comfyui_iframe_id].wait()
        cls.param_events[webui_client_id][comfyui_iframe_id].clear()
        return cls.last_params


def polling_server_patch(instance, loop):
    from aiohttp import web

    ComfyuiNodeWidgetRequests.init_request_listener(loop)

    @instance.routes.post("/sd-webui-comfyui/webui_polling_server")
    async def webui_polling_server(response):
        response = await response.json()
        if 'webui_client_id' not in response:
            return web.json_response(status=422)
        if 'comfyui_iframe_id' not in response:
            return web.json_response(status=422)

        webui_client_id = response['webui_client_id']
        comfyui_iframe_id = response['comfyui_iframe_id']

        if not (webui_client_id in ComfyuiNodeWidgetRequests.comfyui_iframe_ids
                and comfyui_iframe_id in ComfyuiNodeWidgetRequests.comfyui_iframe_ids[webui_client_id]):
            ComfyuiNodeWidgetRequests.add_client(comfyui_iframe_id, webui_client_id)
        else:
            if 'error' in response:
                print(f"[sd-webui-comfyui] Client {comfyui_iframe_id}-{webui_client_id} encountered an error - \n{response['error']}")
            await ComfyuiNodeWidgetRequests.handle_response(response)

        request = await ComfyuiNodeWidgetRequests.handle_request(comfyui_iframe_id, webui_client_id)
        print(f'[sd-webui-comfyui] send request - \n{request}')
        return web.json_response(request)

    @instance.routes.post("/sd-webui-comfyui/set_polling_server_focused_webui_client_id")
    async def set_polling_server_focused_webui_client_id(request):
        request_json = await request.json()
        if 'webui_client_id' not in request_json:
            return web.json_response(status=422)

        webui_client_id = request_json['webui_client_id']
        ComfyuiNodeWidgetRequests.focused_webui_client_id = webui_client_id
        print(f'[sd-webui-comfyui] set client webui_client_id - \n{webui_client_id}')
        return web.json_response()


def add_server__init__patch(callback):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        original_init(self, loop, *args, **kwargs)
        callback(self, loop, *args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__


def patch_server_routes():
    add_server__init__patch(polling_server_patch)
