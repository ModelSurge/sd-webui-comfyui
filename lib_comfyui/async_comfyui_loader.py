import sys
import os
import runpy
from lib_comfyui import (
    argv_conversion,
    custom_extension_injector,
    webui_paths,
    ipc,
    polling_client,
    queue_tracker,
    parallel_utils,
)
import atexit


def main(comfyui_path, webui_folder_paths, process_queues):
    process_queue = process_queues['comfyui']
    ipc.current_process_callback_listeners = {
        'comfyui': parallel_utils.CallbackWatcher(process_queue)
    }
    del process_queues['comfyui']
    ipc.current_process_queues.clear()
    ipc.current_process_queues.update(process_queues)
    ipc.current_process_id = 'comfyui'
    ipc.start_callback_listeners()
    atexit.register(ipc.stop_callback_listeners)
    start_comfyui(comfyui_path, webui_folder_paths)


def start_comfyui(comfyui_path, webui_folder_paths):
    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()

    print('[sd-webui-comfyui]', 'Injecting custom extensions...')
    webui_paths.share_webui_folder_paths(webui_folder_paths)
    patch_comfyui()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, 'main.py'), {}, '__main__')


def patch_comfyui():
    custom_extension_injector.register_webui_extensions()
    polling_client.patch_server_routes()
    queue_tracker.patch_prompt_queue()


