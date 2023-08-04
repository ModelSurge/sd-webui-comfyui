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
    last_request = None
    loop = None
    focused_webui_client_id = None

    @ipc.restrict_to_process('comfyui')
    @staticmethod
    def send(request_params):
        cls = ComfyuiNodeWidgetRequests
        if cls.focused_webui_client_id is None:
            raise RuntimeError('No active webui connection')

        parallel_utils.clear_queue(cls.finished_comfyui_queue)
        webui_client_id = cls.focused_webui_client_id
        cls.last_request = request_params
        cls.loop.call_soon_threadsafe(cls.param_events[webui_client_id][cls.last_request['workflowType']].set)
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
        ComfyuiNodeWidgetRequests.send({
            'request': '/sd-webui-comfyui/webui_request_queue_prompt',
            'workflowType': workflow_type.get_ids(tab)[0],
            'requiredNodeTypes': [],
            'queueFront': queue_front,
        })

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
        try:
            await asyncio.wait_for(cls.param_events[webui_client_id][workflow_type_id].wait(), timeout=0.5)
        except asyncio.TimeoutError:
            return {'request': '/sd-webui-comfyui/webui_request_timeout',}

        cls.param_events[webui_client_id][workflow_type_id].clear()
        print(f'[sd-webui-comfyui] send request - \n{cls.last_request}')
        return cls.last_request


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
        if 'response' not in response:
            return web.json_response(status=422)

        webui_client_id = response['webui_client_id']
        workflow_type_id = response['workflow_type_id']

        if isinstance(response, dict) and 'error' in response['response']:
            print(f"[sd-webui-comfyui] Client {workflow_type_id}-{webui_client_id} encountered an error - \n{response['response']['error']}")

        response_value = response['response']

        if (
            response_value == 'register_cid' or
            webui_client_id not in ComfyuiNodeWidgetRequests.comfyui_iframe_ids or
            workflow_type_id not in ComfyuiNodeWidgetRequests.comfyui_iframe_ids[webui_client_id]
        ):
            ComfyuiNodeWidgetRequests.add_client(workflow_type_id, webui_client_id)

        if response_value not in ('register_cid', 'timeout'):
            await ComfyuiNodeWidgetRequests.handle_response(response)

        request = await ComfyuiNodeWidgetRequests.handle_request(workflow_type_id, webui_client_id)
        return web.json_response(request)


def workflow_ops_server_patch(instance, _loop):
    from aiohttp import web

    @instance.routes.get("/sd-webui-comfyui/default_workflow")
    async def get_default_workflow(request):
        params = request.rel_url.query
        workflow_type_id = params['workflow_type_id']

        try:
            res = web.json_response(external_code.get_default_workflow_json(workflow_type_id))
            return res
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
    add_server__init__patch(workflow_ops_server_patch)
