import asyncio
import multiprocessing
from typing import List
import torch
from lib_comfyui import parallel_utils, ipc, global_state, comfyui_context, torch_utils, external_code
from lib_comfyui.comfyui import queue_tracker
from lib_comfyui.webui import settings


class ComfyuiIFrameRequests:
    finished_comfyui_queue = multiprocessing.Queue()
    workflow_type_ids = {}
    param_events = {}
    last_request = None
    loop = None
    focused_webui_client_id = None

    @ipc.restrict_to_process('comfyui')
    @staticmethod
    def send(request_params):
        cls = ComfyuiIFrameRequests
        if cls.focused_webui_client_id is None:
            raise RuntimeError('No active webui connection')

        webui_client_id = cls.focused_webui_client_id
        cls.last_request = request_params
        parallel_utils.clear_queue(cls.finished_comfyui_queue)
        cls.loop.call_soon_threadsafe(cls.param_events[webui_client_id][cls.last_request['workflowType']].set)
        return cls.finished_comfyui_queue.get()

    @ipc.run_in_process('comfyui')
    @staticmethod
    def start_workflow_sync(
        batch_input: List[torch.Tensor],
        workflow_type_id: str,
        queue_front: bool,
    ):
        if settings.shared_state.interrupted:
            return batch_input

        global_state.node_inputs = batch_input
        global_state.node_outputs = []

        queue_tracker.setup_tracker_id()

        # unsafe queue tracking
        ComfyuiIFrameRequests.send({
            'request': '/sd-webui-comfyui/webui_request_queue_prompt',
            'workflowType': workflow_type_id,
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

    @classmethod
    async def handle_response(cls, response):
        cls.finished_comfyui_queue.put(response)