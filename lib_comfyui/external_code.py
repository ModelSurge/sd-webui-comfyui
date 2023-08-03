import dataclasses
from typing import List, Tuple, Union
from lib_comfyui import global_state, ipc


ALL_TABS = ('txt2img', 'img2img')
Tabs = Union[str, Tuple[str]]


@dataclasses.dataclass
class Workflow:
    base_id: str
    display_name: str
    tabs: Tabs = ALL_TABS
    default_workflow: dict = None

    def __post_init__(self):
        if isinstance(self.tabs, str):
            self.tabs = (self.tabs,)

    def get_ids(self, tabs: Tabs = ALL_TABS) -> List[str]:
        if isinstance(tabs, str):
            tabs = (tabs,)

        return [
            f'{self.base_id}_{tab}'
            for tab in self.tabs
            if tab in tabs
        ]


def add_workflow(new_workflow: Workflow) -> None:
    """
    Register a new workflow type
    You can also call this function to dynamically add a workflow type in the ui
    """
    workflows = get_workflows()

    for existing_workflow in workflows:
        if existing_workflow.base_id == new_workflow.base_id:
            raise ValueError(f'The workflow id {new_workflow.base_id} already exists')
        if existing_workflow.display_name == new_workflow.display_name:
            raise ValueError(f'The workflow display name {new_workflow.display_name} is already in use by workflow {existing_workflow.base_id}')

    if getattr(global_state, 'is_ui_instantiated', False):
        raise NotImplementedError('Cannot yet modify workflows after the ui has been instantiated')

    workflows.append(new_workflow)
    set_workflows(workflows)


def get_workflows(tabs: Tabs = ALL_TABS) -> List[Workflow]:
    """
    Get the list of currently registered workflows
    To update the workflows, do not modify this list directly
    Instead, have a look at the other functions
    """
    if isinstance(tabs, str):
        tabs = (tabs,)

    return [
        workflow
        for workflow in getattr(global_state, 'workflows', [])
        if any(tab in tabs for tab in workflow.tabs)
    ]


def set_workflows(workflows: List[Workflow]) -> None:
    if getattr(global_state, 'is_ui_instantiated', False):
        raise NotImplementedError('Cannot yet modify workflows after the ui has been instantiated')

    setattr(global_state, 'workflows', workflows)


def get_workflow_ids(tabs: Tabs = ALL_TABS) -> List[str]:
    res = []

    for workflow in get_workflows(tabs):
        res.extend(workflow.get_ids(tabs))

    return res


def get_workflow_display_names(tabs: Tabs = ALL_TABS) -> List[str]:
    return [workflow.display_name for workflow in get_workflows(tabs)]


def get_iframe_id(workflow_id: str) -> str:
    return f'comfyui_{workflow_id}'
