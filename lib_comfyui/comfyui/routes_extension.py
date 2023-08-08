import asyncio
import json
import traceback
from typing import List
import torch
from lib_comfyui import parallel_utils, ipc, global_state, torch_utils, external_code
from lib_comfyui.comfyui import queue_tracker
from lib_comfyui.webui import settings


# rest is ran on comfyui's server side
class ComfyuiIFrameRequests:
    workflow_type_ids = {}
    param_events = {}
    last_request = None
    loop = None
    focused_webui_client_id = None

    @ipc.run_in_process('comfyui')
    @staticmethod
    def send(request_params):
        cls = ComfyuiIFrameRequests
        if cls.focused_webui_client_id is None:
            raise RuntimeError('No active webui connection')

        events = cls.param_events[cls.focused_webui_client_id]
        if request_params['workflowType'] not in events:
            raise RuntimeError(f"The workflow type {cls.last_request['workflowType']} has not been registered by the active webui client {cls.focused_webui_client_id}")

        cls.last_request = request_params
        event = events[request_params['workflowType']]
        cls.loop.call_soon_threadsafe(event.set)

    @ipc.restrict_to_process('webui')
    @staticmethod
    def start_workflow_sync(
        batch_input: List[torch.Tensor],
        workflow_type_id: str,
        queue_front: bool,
    ):
        from modules import shared
        if shared.state.interrupted:
            return batch_input

        global_state.node_inputs = batch_input
        global_state.node_outputs = []

        queue_tracker.setup_tracker_id()

        # unsafe queue tracking
        try:
            ComfyuiIFrameRequests.send({
                'request': '/sd-webui-comfyui/webui_request_queue_prompt',
                'workflowType': workflow_type_id,
                'requiredNodeTypes': [],
                'queueFront': queue_front,
            })
        except RuntimeError as e:
            print('\n'.join(traceback.format_exception_only(e)))
            return batch_input

        queue_tracker.wait_until_done()

        return global_state.node_outputs

    @classmethod
    def init_request_listener(cls, loop):
        if loop is None or cls.loop is not None:
            return

        cls.loop = loop

    @classmethod
    def add_client(cls, workflow_type_id, webui_client_id):
        if webui_client_id not in cls.workflow_type_ids:
            cls.workflow_type_ids[webui_client_id] = set()
        if webui_client_id not in cls.param_events:
            cls.param_events[webui_client_id] = {}
        if workflow_type_id in cls.workflow_type_ids[webui_client_id]:
            return

        # REMOVE THIS AT SOME POINT
        ComfyuiIFrameRequests.focused_webui_client_id = webui_client_id

        cls.param_events[webui_client_id][workflow_type_id] = asyncio.Event()
        cls.workflow_type_ids[webui_client_id].add(workflow_type_id)
        print(f'[sd-webui-comfyui] registered new ComfyUI client - {workflow_type_id}')

    @classmethod
    async def create_client_request(cls, workflow_type_id, webui_client_id):
        client_event = cls.param_events[webui_client_id][workflow_type_id]
        try:
            await asyncio.wait_for(client_event.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            return {'request': '/sd-webui-comfyui/webui_request_timeout',}

        client_event.clear()
        print(f'[sd-webui-comfyui] send request - \n{cls.last_request}')
        return cls.last_request


def polling_server_patch(instance, loop):
    from aiohttp import web

    ComfyuiIFrameRequests.init_request_listener(loop)

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
            webui_client_id not in ComfyuiIFrameRequests.workflow_type_ids or
            workflow_type_id not in ComfyuiIFrameRequests.workflow_type_ids[webui_client_id]
        ):
            ComfyuiIFrameRequests.add_client(workflow_type_id, webui_client_id)

        request = await ComfyuiIFrameRequests.create_client_request(workflow_type_id, webui_client_id)
        return web.json_response(request)


def workflow_type_ops_server_patch(instance, _loop):
    from aiohttp import web

    @instance.routes.get("/sd-webui-comfyui/default_workflow")
    async def get_default_workflow(request):
        params = request.rel_url.query
        workflow_type_id = params['workflow_type_id']

        try:
            res = web.json_response(json.loads(external_code.get_default_workflow_json(workflow_type_id)))
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
    add_server__init__patch(workflow_type_ops_server_patch)
