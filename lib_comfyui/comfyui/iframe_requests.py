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
    focused_webui_client_id = None
    server_instance = None
    sid_map = {}

    @staticmethod
    @ipc.run_in_process('comfyui')
    def send(request, workflow_type, data={}):
        cls = ComfyuiIFrameRequests
        if cls.focused_webui_client_id is None:
            raise RuntimeError('No active webui connection')

        ws_client_ids = cls.sid_map[cls.focused_webui_client_id]
        if workflow_type not in ws_client_ids:
            raise RuntimeError(f"The workflow type {workflow_type} has not been registered by the active webui client {cls.focused_webui_client_id}")

        clear_queue(cls.finished_comfyui_queue)
        cls.server_instance.send_sync(request, data, ws_client_ids[workflow_type])

        return cls.finished_comfyui_queue.get()

    @staticmethod
    @ipc.restrict_to_process('webui')
    def start_workflow_sync(
        batch_input: torch.Tensor,
        workflow_type_id: str,
        queue_front: bool,
    ) -> List[torch.Tensor]:
        from modules import shared
        if shared.state.interrupted:
            return [batch_input]

        if is_default_workflow(workflow_type_id):
            print('[sd-webui-comfyui]', f'Skipping workflow {workflow_type_id} because it is empty.')
            return [batch_input]

        global_state.node_inputs = batch_input
        global_state.node_outputs = []

        queue_tracker.setup_tracker_id()

        # unsafe queue tracking
        try:
            ComfyuiIFrameRequests.send(
                request='webui_queue_prompt',
                workflow_type=workflow_type_id,
                data={
                    'requiredNodeTypes': [],
                    'queueFront': queue_front,
                }
            )
        except RuntimeError as e:
            print('\n'.join(traceback.format_exception_only(e)))
            return [batch_input]

        if not queue_tracker.wait_until_done():
            return [batch_input]

        return global_state.node_outputs

    @staticmethod
    @ipc.restrict_to_process('comfyui')
    def register_client(request):
        workflow_type_id = request['workflowTypeId']
        webui_client_id = request['webuiClientId']
        sid = request['sid']

        # TODO: generalize this
        ComfyuiIFrameRequests.focused_webui_client_id = webui_client_id

        if webui_client_id not in ComfyuiIFrameRequests.sid_map:
            ComfyuiIFrameRequests.sid_map[webui_client_id] = {}

        ComfyuiIFrameRequests.sid_map[webui_client_id][workflow_type_id] = sid

        print(f'registered ws - {workflow_type_id} - {sid}')

    @staticmethod
    @ipc.restrict_to_process('comfyui')
    def handle_response(response):
        ComfyuiIFrameRequests.finished_comfyui_queue.put(response)


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
    if not all(current_graph['nodes'][i]['type'] == default_graph['nodes'][i]['type'] for i in range(nodes_len)):
        return False

    def create_adjacency_matrix(graph):
        adjacency_matrix = torch.zeros((nodes_len,) * 2, dtype=torch.bool)
        for i, i_node in enumerate(graph['nodes']):
            for j, j_node in enumerate(graph['nodes']):
                if i == j:
                    continue

                adjacency_matrix[i, j] = any(
                    link[1] == i_node['id'] and link[3] == j_node['id']
                    for link in graph['links']
                )

        return adjacency_matrix

    default_adjacency_matrix = create_adjacency_matrix(default_graph)
    current_adjacency_matrix = create_adjacency_matrix(current_graph)
    return (current_adjacency_matrix == default_adjacency_matrix).all()


def extend_infotext_with_comfyui_workflows(p, tab):
    workflows = {}
    for workflow_type in external_code.get_workflow_types(tab):
        workflow_type_id = workflow_type.get_ids(tab)[0]
        if not getattr(global_state, 'enabled_workflow_type_ids', {}).get(workflow_type_id, False):
            continue

        graph = get_workflow_graph(workflow_type_id)
        if is_default_workflow(workflow_type_id, graph):
            continue

        workflows[workflow_type.base_id] = graph

    p.extra_generation_params['ComfyUI Workflows'] = json.dumps(workflows)


def set_workflow_graph(workflow_json, workflow_type_id):
    return ComfyuiIFrameRequests.send(
        request='webui_set_workflow',
        workflow_type=workflow_type_id,
        data={'workflow': workflow_json}
    )


def get_workflow_graph(workflow_type_id):
    return ComfyuiIFrameRequests.send(request='webui_serialize_graph', workflow_type=workflow_type_id)


def clear_queue(queue: multiprocessing.Queue):
    while not queue.empty():
        try:
            queue.get(timeout=1)
        except Empty:
            pass
