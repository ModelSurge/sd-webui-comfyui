import dataclasses
from pathlib import Path
from typing import List, Tuple, Union, Any, Optional
from lib_comfyui import global_state


ALL_TABS = ...
Tabs = Union[str, Tuple[str]]


@dataclasses.dataclass
class WorkflowType:
    base_id: str
    display_name: str
    tabs: Tabs = ('txt2img', 'img2img')
    default_workflow: Union[str, Path] = "null"

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

    def pretty_str(self):
        return f'"{self.display_name}" ({self.base_id})'


def get_workflow_types(tabs: Tabs = ALL_TABS) -> List[WorkflowType]:
    """
    Get the list of currently registered workflow types
    To update the workflow types list, see `add_workflow_type` or `set_workflow_types`

    Args:
        tabs (Tabs): Whitelist of tabs
    Returns:
        List of workflow types that are defined on at least one of the given tabs
    """
    if isinstance(tabs, str):
        tabs = (tabs,)

    return [
        workflow_type
        for workflow_type in getattr(global_state, 'workflow_types', [])
        if tabs == ALL_TABS or any(tab in tabs for tab in workflow_type.tabs)
    ]


def add_workflow_type(new_workflow_type: WorkflowType) -> None:
    """
    Register a new workflow type
    You cannot call this function after the extension ui has been created

    Args:
        new_workflow_type (WorkflowType): new workflow type to add
    Raises:
        ValueError: If the id or display_name of new_workflow_type has already been registered
        NotImplementedError: if the workflow types list is modified after the ui has been instantiated
    """
    workflow_types = get_workflow_types()

    for existing_workflow_type in workflow_types:
        if existing_workflow_type.base_id == new_workflow_type.base_id:
            raise ValueError(f'The id {new_workflow_type.base_id} already exists')
        if existing_workflow_type.display_name == new_workflow_type.display_name:
            raise ValueError(f'The display name {new_workflow_type.display_name} is already in use by workflow type {existing_workflow_type.base_id}')

    if getattr(global_state, 'is_ui_instantiated', False):
        raise NotImplementedError('Cannot modify workflow types after the ui has been instantiated')

    workflow_types.append(new_workflow_type)
    set_workflow_types(workflow_types)


def set_workflow_types(workflow_types: List[WorkflowType]) -> None:
    """
    Set the list of currently registered workflow types
    You cannot call this function after the extension ui has been created
    Args:
        workflow_types (List[WorkflowType]): the new workflow types
    Raises:
        NotImplementedError: if the workflow types list is modified after the ui has been instantiated
    Notes:
        A deep copy of workflow_types is used when calling this function from the comfyui process
        No copy is made when calling this function from the webui process
    """
    if getattr(global_state, 'is_ui_instantiated', False):
        raise NotImplementedError('Cannot modify workflow types after the ui has been instantiated')

    global_state.workflow_types = workflow_types


def clear_workflow_types() -> None:
    """
    Clear the list of currently registered workflow types
    You cannot call this function after the extension ui has been created
    Raises:
        NotImplementedError: if the workflow types list is modified after the ui has been instantiated
    """
    set_workflow_types([])


def get_workflow_type_ids(tabs: Tabs = ALL_TABS) -> List[str]:
    """
    Get all workflow type ids of all currently registered workflow types
    Multiple ids can be assigned to each workflow type depending on how many tabs it is to be displayed on

    Args:
        tabs (Tabs): Whitelist of tabs for which to return the ids
    Returns:
        List of ids for the given tabs
    """
    res = []

    for workflow_type in get_workflow_types(tabs):
        res.extend(workflow_type.get_ids(tabs))

    return res


def get_workflow_type_display_names(tabs: Tabs = ALL_TABS) -> List[str]:
    """
    Get the list of display names needed for the given tabs

    Args:
        tabs (Tabs): Whitelist of tabs for which to return the display names
    Returns:
        List of display names for the given tabs
    """
    return [workflow_type.display_name for workflow_type in get_workflow_types(tabs)]


def get_default_workflow_json(workflow_type_id: str) -> str:
    """
    Get the default workflow for the given workflow type id

    Args:
        workflow_type_id (str): The workflow type id for which to get the default workflow
    Returns:
        The default workflow, or None if there is no default workflow for the given workflow type
    Raises:
        ValueError: If workflow_type_id does not exist
    """
    for workflow_type in get_workflow_types():
        if workflow_type_id in workflow_type.get_ids():
            return workflow_type.default_workflow

    raise ValueError(workflow_type_id)


def run_workflow(
    workflow_type: WorkflowType,
    tab: str,
    batch_input: List[Any],
    queue_front: Optional[bool] = None,
) -> List[Any]:
    """
    Run a comfyui workflow synchronously

    Args:
        workflow_type (WorkflowType): Target workflow type to run
        tab (str): The tab on which to run the workflow type. The workflow type must be present on the tab
        batch_input (List[ANy]): Batch objects to pass to the workflow. The number of elements in batch_input is the size of the comfyui batch
        queue_front (Optional[bool]): Whether to queue the workflow before or after the currently queued workflows
    Returns:
        The output of the workflow. The size of the output does not necessarily match len(batch_input)
    Raises:
        ValueError: If workflow_type is not present on the given tab
        AssertionError: If multiple candidate ids exist for workflow_type
    """
    from lib_comfyui.comfyui.routes_extension import ComfyuiNodeWidgetRequests

    if queue_front is None:
        queue_front = getattr(global_state, 'queue_front', True)

    candidate_ids = workflow_type.get_ids(tab)
    assert len(candidate_ids) <= 1, f'Found multiple candidate workflow type ids for tab {tab} and workflow type {workflow_type.pretty_str()}: {candidate_ids}'

    if not candidate_ids:
        raise ValueError(f'Incompatible tab {tab} and workflow type {workflow_type.pretty_str()}. Valid tabs for the given workflow type: {workflow_type.tabs}')

    return ComfyuiNodeWidgetRequests.start_workflow_sync(
        batch_input=batch_input,
        workflow_type_id=candidate_ids[0],
        queue_front=queue_front,
    )
