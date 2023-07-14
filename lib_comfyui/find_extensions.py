import os.path
from modules.extensions import list_extensions, active


def get_extension_paths_to_load():
    list_extensions()
    active_paths = [e.path for e in active()]
    root_node_paths = []
    root_script_paths = []

    for path in active_paths:
        root_nodes = os.path.join(path, 'comfyui_custom_nodes')
        root_scripts = os.path.join(path, 'comfyui_custom_scripts')
        if os.path.exists(root_nodes):
            root_node_paths.append(root_nodes)
        if os.path.exists(root_scripts):
            root_script_paths.append(root_scripts)

    return root_node_paths, root_script_paths
