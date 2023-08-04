import dataclasses
import json
from pathlib import Path
from typing import List, Tuple, Union
from lib_comfyui import global_state


ALL_TABS = ...
Tabs = Union[str, Tuple[str]]


@dataclasses.dataclass
class WorkflowType:
    base_id: str
    display_name: str
    tabs: Tabs = ('txt2img', 'img2img')
    default_workflow: Union[str, Path] = json.dumps(None)

    def __post_init__(self):
        if isinstance(self.tabs, str):
            self.tabs = (self.tabs,)

        assert self.tabs, "tabs must not be empty"

        if isinstance(self.default_workflow, Path):
            with open(str(self.default_workflow), 'r') as f:
                self.default_workflow = f.read()

    def get_ids(self, tabs: Tabs = ALL_TABS) -> List[str]:
        if isinstance(tabs, str):
            tabs = (tabs,)

        return [
            f'{self.base_id}_{tab}'
            for tab in self.tabs
            if tabs == ALL_TABS or tab in tabs
        ]


def add_workflow_type(new_workflow_type: WorkflowType) -> None:
    """
    Register a new workflow type
    You cannot call this function after the extension ui has been created
    """
    workflows = get_workflow_types()

    for existing_workflow in workflows:
        if existing_workflow.base_id == new_workflow_type.base_id:
            raise ValueError(f'The id {new_workflow_type.base_id} already exists')
        if existing_workflow.display_name == new_workflow_type.display_name:
            raise ValueError(f'The display name {new_workflow_type.display_name} is already in use by workflow type {existing_workflow.base_id}')

    if getattr(global_state, 'is_ui_instantiated', False):
        raise NotImplementedError('Cannot modify workflow types after the ui has been instantiated')

    workflows.append(new_workflow_type)
    set_workflow_types(workflows)


def get_workflow_types(tabs: Tabs = ALL_TABS) -> List[WorkflowType]:
    """
    Get the list of currently registered workflows
    To update the workflows list, see `add_workflow_type` or `set_workflow_types`
    """
    if isinstance(tabs, str):
        tabs = (tabs,)

    return [
        workflow_type
        for workflow_type in getattr(global_state, 'workflow_types', [])
        if tabs == ALL_TABS or any(tab in tabs for tab in workflow_type.tabs)
    ]


def set_workflow_types(workflows: List[WorkflowType]) -> None:
    """
    Set the list of currently registered workflows
    You cannot call this function after the extension ui has been created
    """
    if getattr(global_state, 'is_ui_instantiated', False):
        raise NotImplementedError('Cannot modify workflow types after the ui has been instantiated')

    global_state.workflow_types = workflows


def clear_workflow_types() -> None:
    """
    Clear the list of currently registered workflows
    You cannot call this function after the extension ui has been created
    """
    global_state.workflow_types = []


def get_workflow_type_ids(tabs: Tabs = ALL_TABS) -> List[str]:
    """
    Get all workflow type ids of all currently registered workflows
    Multiple ids can be assigned to each workflow type depending on how many tabs it is to be displayed on

    Args:
        tabs (Tabs): whitelist of tabs for which to return the ids
    Returns:
        list of ids for the given tabs
    """
    res = []

    for workflow_type in get_workflow_types(tabs):
        res.extend(workflow_type.get_ids(tabs))

    return res


def get_workflow_type_display_names(tabs: Tabs = ALL_TABS) -> List[str]:
    """
    Get the list of display names for
    """
    return [workflow_type.display_name for workflow_type in get_workflow_types(tabs)]


def get_default_workflow_json(workflow_type_id: str) -> dict:
    for workflow_type in get_workflow_types():
        if workflow_type_id in workflow_type.get_ids():
            return json.loads(workflow_type.default_workflow)

    raise ValueError(workflow_type_id)
