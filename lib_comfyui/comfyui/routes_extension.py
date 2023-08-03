import asyncio
import multiprocessing
from typing import List
import torch
from lib_comfyui import parallel_utils, ipc, global_state, comfyui_context, torch_utils, external_code
from lib_comfyui.comfyui import queue_tracker


# rest is ran on comfyui's server side
class ComfyuiNodeWidgetRequests:
    start_comfyui_queue = multiprocessing.Queue()
    finished_comfyui_queue = multiprocessing.Queue()
    comfyui_iframe_ids = {}
    param_events = {}
    last_params = None
    loop = None
    focused_webui_client_id = None

    @ipc.restrict_to_process('comfyui')
    @staticmethod
    def send(request_params):
        cls = ComfyuiNodeWidgetRequests
        if cls.focused_webui_client_id is None:
            return None
        parallel_utils.clear_queue(cls.finished_comfyui_queue)
        webui_client_id = cls.focused_webui_client_id
        cls.last_params = request_params
        cls.loop.call_soon_threadsafe(cls.param_events[webui_client_id][cls.last_params['workflowType']].set)
        result = cls.finished_comfyui_queue.get(timeout=10)

        return result

    @ipc.run_in_process('comfyui')
    @staticmethod
    def start_workflow_sync(
        input_batch: List[torch.Tensor],
        workflow_type: external_code.WorkflowType,
        tab: str,
        queue_front: bool,
    ):
        global_state.node_inputs = input_batch
        global_state.node_outputs = []

        queue_tracker.setup_tracker_id()

        # unsafe queue tracking
        response = ComfyuiNodeWidgetRequests.send({
            'request': '/sd-webui-comfyui/webui_request_queue_prompt',
            'workflowType': workflow_type.get_ids(tab)[0],
            'requiredNodeTypes': [],
            'queueFront': queue_front,
        })

        if response is None or 'error' in response:
            return response

        queue_tracker.wait_until_done()

        return global_state.node_outputs

    @classmethod
    def init_request_listener(cls, loop):
        if loop is None or cls.loop is not None:
            return

        cls.loop = loop

    @classmethod
    def add_client(cls, workflow_type_id, webui_client_id):
        if webui_client_id not in cls.comfyui_iframe_ids:
            cls.comfyui_iframe_ids[webui_client_id] = set()
        if webui_client_id not in cls.param_events:
            cls.param_events[webui_client_id] = {}
        if workflow_type_id in cls.comfyui_iframe_ids[webui_client_id]:
            return

        # REMOVE THIS AT SOME POINT
        ComfyuiNodeWidgetRequests.focused_webui_client_id = webui_client_id

        cls.param_events[webui_client_id][workflow_type_id] = asyncio.Event()
        cls.comfyui_iframe_ids[webui_client_id].add(workflow_type_id)
        print(f'[sd-webui-comfyui] registered new ComfyUI client - {workflow_type_id}')

    @classmethod
    async def handle_response(cls, response):
        cls.finished_comfyui_queue.put(response)

    @classmethod
    async def handle_request(cls, workflow_type_id, webui_client_id):
        await cls.param_events[webui_client_id][workflow_type_id].wait()
        cls.param_events[webui_client_id][workflow_type_id].clear()
        return cls.last_params


def polling_server_patch(instance, loop):
    from aiohttp import web

    ComfyuiNodeWidgetRequests.init_request_listener(loop)

    @instance.routes.post("/sd-webui-comfyui/webui_polling_server")
    async def webui_polling_server(response):
        response = await response.json()
        if 'webui_client_id' not in response:
            return web.json_response(status=422)
        if 'workflow_type_id' not in response:
            return web.json_response(status=422)

        webui_client_id = response['webui_client_id']
        workflow_type_id = response['workflow_type_id']

        if not (webui_client_id in ComfyuiNodeWidgetRequests.comfyui_iframe_ids
                and workflow_type_id in ComfyuiNodeWidgetRequests.comfyui_iframe_ids[webui_client_id]):
            ComfyuiNodeWidgetRequests.add_client(workflow_type_id, webui_client_id)
        else:
            if 'error' in response:
                print(f"[sd-webui-comfyui] Client {workflow_type_id}-{webui_client_id} encountered an error - \n{response['error']}")
            await ComfyuiNodeWidgetRequests.handle_response(response)

        request = await ComfyuiNodeWidgetRequests.handle_request(workflow_type_id, webui_client_id)
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

    @instance.routes.get("/sd-webui-comfyui/default_workflow")
    async def get_default_workflow(request):
        params = request.rel_url.query
        workflow_type_id = params['workflow_type_id']

        try:
            return web.json_response(external_code.get_default_workflow_json(workflow_type_id))
        except ValueError as e:
            return web.json_response(status=422, reason=str(e))


def add_server__init__patch(callback):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        original_init(self, loop, *args, **kwargs)
        callback(self, loop, *args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__


def patch_server_routes():
    add_server__init__patch(polling_server_patch)
