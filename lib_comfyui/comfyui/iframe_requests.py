import asyncio
import json
import multiprocessing
import traceback
import torch
from queue import Empty
from typing import List
from lib_comfyui import ipc, global_state, torch_utils, external_code
from lib_comfyui.comfyui import queue_tracker


class ComfyuiIFrameRequests:
    finished_comfyui_queue = multiprocessing.Queue()
    workflow_type_ids = {}
    param_events = {}
    last_request = None
    loop = None
    focused_webui_client_id = None

    @staticmethod
    @ipc.run_in_process('comfyui')
    def send(request_params):
        cls = ComfyuiIFrameRequests
        if cls.focused_webui_client_id is None:
            raise RuntimeError('No active webui connection')

        events = cls.param_events[cls.focused_webui_client_id]
        if request_params['workflowType'] not in events:
            raise RuntimeError(f"The workflow type {cls.last_request['workflowType']} has not been registered by the active webui client {cls.focused_webui_client_id}")

        cls.last_request = request_params
        clear_queue(cls.finished_comfyui_queue)
        event = events[request_params['workflowType']]
        cls.loop.call_soon_threadsafe(event.set)
        return cls.finished_comfyui_queue.get()

    @staticmethod
    @ipc.restrict_to_process('webui')
    def start_workflow_sync(
        batch_input: List[torch.Tensor],
        workflow_type_id: str,
        queue_front: bool,
    ):
        from modules import shared
        if shared.state.interrupted:
            return batch_input

        if is_default_workflow(workflow_type_id):
            print('[sd-webui-comfyui]', f'Skipping workflow {workflow_type_id} because it is empty.')
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

    @classmethod
    async def handle_response(cls, response):
        cls.finished_comfyui_queue.put(response)


def is_default_workflow(workflow_type_id, current_graph=None):
    if current_graph is None:
        current_graph = get_workflow_graph(workflow_type_id)

    default_graph = json.loads(external_code.get_default_workflow_json(workflow_type_id))
    nodes_len = len(current_graph['nodes'])
    if nodes_len != len(default_graph['nodes']):
        return False

    if len(current_graph['links']) != len(default_graph['links']):
        return False

    current_graph['nodes'].sort(key=lambda e: e['type'])
    default_graph['nodes'].sort(key=lambda e: e['type'])

    def create_adjacency_matrix(graph):
        adjacency_matrix = torch.zeros((nodes_len,) * 2, dtype=torch.bool)
        for i, i_node in enumerate(graph['nodes']):
            for j, j_node in enumerate(graph['nodes']):
                if i == j:
                    continue

                adjacency_matrix[i, j] = any(link[1] == i_node['id'] and link[3] == j_node['id'] for link in graph['links'])

        return adjacency_matrix

    default_adjacency_matrix = create_adjacency_matrix(default_graph)
    current_adjacency_matrix = create_adjacency_matrix(current_graph)
    return (current_adjacency_matrix == default_adjacency_matrix).all()


def extend_infotext_with_comfyui_workflows(p, tab):
    workflows = {}
    for workflow_type in external_code.get_workflow_types(tab):
        workflow_type_id = workflow_type.get_ids(tab)[0]
        graph = get_workflow_graph(workflow_type_id)
        if is_default_workflow(workflow_type_id, graph):
            continue

        workflows[workflow_type.base_id] = graph

    p.extra_generation_params['ComfyUI Workflows'] = json.dumps(workflows)


def set_workflow_graph(workflow_json, workflow_type_id):
    return ComfyuiIFrameRequests.send({
        'request': '/sd-webui-comfyui/webui_request_set_workflow',
        'workflowType': workflow_type_id,
        'workflow': workflow_json,
    })


def get_workflow_graph(workflow_type_id):
    return ComfyuiIFrameRequests.send({
        'request': '/sd-webui-comfyui/webui_request_serialize_graph',
        'workflowType': workflow_type_id,
    })


def clear_queue(queue: multiprocessing.Queue):
    while not queue.empty():
        try:
            queue.get(timeout=1)
        except Empty:
            pass
