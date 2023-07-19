import sys
import os
import runpy
from lib_comfyui import argv_conversion, custom_extension_injector, webui_paths, parallel_utils


def main(comfyui_path, process_queues):
    parallel_utils.process_queues.update(process_queues)
    parallel_utils.current_process_id = 'comfyui'
    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    folder_paths = webui_paths.get_folder_paths()

    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()

    webui_paths.share_webui_folder_paths(folder_paths)
    custom_extension_injector.register_webui_extensions()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, 'main.py'), {}, '__main__')
