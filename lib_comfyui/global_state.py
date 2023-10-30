import sys
from types import ModuleType
from typing import List, Tuple, Dict, Any
from lib_comfyui import ipc


enabled: bool
is_ui_instantiated: bool
queue_front: bool
focused_webui_client_id: str

workflow_types: List
enabled_workflow_type_ids: Dict[str, bool]
node_inputs: Tuple[Any, ...]
node_outputs: List[Dict[str, Any]]
current_workflow_input_types: Tuple[str, ...]

ipc_strategy_class: type
ipc_strategy_class_name: str
comfyui_graceful_termination_timeout: float

reverse_proxy_enabled: bool

last_positive_prompt: str
last_negative_prompt: str


class GlobalState(ModuleType):
    __state = {}

    def __init__(self, glob):
        super().__init__(__name__)
        for k, v in glob.items():
            setattr(self, k, v)

    def __getattr__(self, item):
        if item in ['__file__']:
            return globals()[item]

        return GlobalState.getattr(item)

    @staticmethod
    @ipc.run_in_process('webui')
    def getattr(item):
        try:
            return GlobalState.__state[item]
        except KeyError:
            raise AttributeError

    def __setattr__(self, item, value):
        GlobalState.setattr(item, value)

    @staticmethod
    @ipc.run_in_process('webui')
    def setattr(item, value):
        GlobalState.__state[item] = value

    def __delattr__(self, item):
        GlobalState.delattr(item)

    @staticmethod
    @ipc.run_in_process('webui')
    def delattr(item):
        del GlobalState.__state[item]

    def __contains__(self, item):
        return GlobalState.contains(item)

    @staticmethod
    @ipc.run_in_process('webui')
    def contains(item):
        return item in GlobalState.__state


sys.modules[__name__] = GlobalState(globals())
