import json
import multiprocessing
from queue import Empty
from typing import List, Any, Dict, Tuple
from lib_comfyui import ipc, global_state, torch_utils, external_code
from lib_comfyui.comfyui import queue_tracker


class ComfyuiIFrameRequests:
    finished_comfyui_queue = multiprocessing.Queue()
    server_instance = None
    sid_map = {}

    @staticmethod
    @ipc.run_in_process('comfyui')
    def send(request, workflow_type, data=None):
        if data is None:
            data = {}

        cls = ComfyuiIFrameRequests
        if global_state.focused_webui_client_id is None:
            raise RuntimeError('No active webui connection')

        ws_client_ids = cls.sid_map[global_state.focused_webui_client_id]
        if workflow_type not in ws_client_ids:
            raise RuntimeError(f"The workflow type {workflow_type} has not been registered by the active webui client {global_state.focused_webui_client_id}")

        clear_queue(cls.finished_comfyui_queue)
        cls.server_instance.send_sync(request, data, ws_client_ids[workflow_type])

        return cls.finished_comfyui_queue.get()

    @staticmethod
    @ipc.restrict_to_process('webui')
    def start_workflow_sync(
        batch_input_args: Tuple[Any, ...],
        workflow_type_id: str,
        workflow_input_types: List[str],
        queue_front: bool,
    ) -> List[Dict[str, Any]]:
        from modules import shared
        if shared.state.interrupted:
            raise RuntimeError('The workflow was not started because the webui has been interrupted')

        global_state.node_inputs = batch_input_args
        global_state.node_outputs = []
        global_state.current_workflow_input_types = workflow_input_types

        try:
            queue_tracker.setup_tracker_id()

            # unsafe queue tracking
            ComfyuiIFrameRequests.send(
                request='webui_queue_prompt',
                workflow_type=workflow_type_id,
                data={
                    'requiredNodeTypes': [],
                    'queueFront': queue_front,
                }
            )

            if not queue_tracker.wait_until_done():
                raise RuntimeError('The workflow has not returned normally')

            return global_state.node_outputs
        finally:
            global_state.current_workflow_input_types = ()
            global_state.node_outputs = []
            global_state.node_inputs = None

    @staticmethod
    @ipc.restrict_to_process('comfyui')
    def register_client(request):
        workflow_type_id = request['workflowTypeId']
        webui_client_id = request['webuiClientId']
        sid = request['sid']

        if webui_client_id not in ComfyuiIFrameRequests.sid_map:
            ComfyuiIFrameRequests.sid_map[webui_client_id] = {}

        ComfyuiIFrameRequests.sid_map[webui_client_id][workflow_type_id] = sid

        print(f'registered ws - {workflow_type_id} - {sid}')

    @staticmethod
    @ipc.restrict_to_process('comfyui')
    def handle_response(response):
        ComfyuiIFrameRequests.finished_comfyui_queue.put(response)


def extend_infotext_with_comfyui_workflows(p, tab):
    workflows = {}
    for workflow_type in external_code.get_workflow_types(tab):
        workflow_type_id = workflow_type.get_ids(tab)[0]
        if not external_code.is_workflow_type_enabled(workflow_type_id):
            continue

        workflows[workflow_type.base_id] = get_workflow_graph(workflow_type_id)

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
