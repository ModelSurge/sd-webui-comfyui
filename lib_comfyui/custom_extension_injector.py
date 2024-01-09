import os
from lib_comfyui import find_extensions, ipc


def register_webui_extensions():
    node_paths, script_paths = find_extensions.get_extension_paths_to_load()
    register_custom_nodes(node_paths)
    register_custom_scripts(script_paths)


@ipc.restrict_to_process('comfyui')
def register_custom_nodes(custom_nodes_path_list):
    from folder_paths import add_model_folder_path

    for custom_nodes_path in custom_nodes_path_list:
        add_model_folder_path('custom_nodes', custom_nodes_path)


@ipc.restrict_to_process('comfyui')
def register_custom_scripts(custom_scripts_path_list):
    if not custom_scripts_path_list:
        return

    from nodes import EXTENSION_WEB_DIRS

    for custom_scripts_path in custom_scripts_path_list:
        name = f"webui_scripts/{os.path.basename(os.path.dirname(custom_scripts_path))}"
        dir = custom_scripts_path
        EXTENSION_WEB_DIRS[name] = dir
