import atexit
import builtins
import sys
import os
import runpy
from lib_comfyui import (
    custom_extension_injector,
    ipc,
    parallel_utils,
)
from lib_comfyui.comfyui import routes_extension, queue_tracker
from lib_comfyui.webui import paths


original_print = builtins.print
def comfyui_print(*args, **kwargs):
    return original_print('[ComfyUI]', *args, **kwargs)


def main():
    builtins.print = comfyui_print
    ipc.current_callback_listeners = {'comfyui': parallel_utils.CallbackWatcher(ipc.call_fully_qualified, 'comfyui')}
    ipc.current_callback_proxies = {'webui': parallel_utils.CallbackProxy('webui')}
    ipc.current_process_id = 'comfyui'
    atexit.register(ipc.stop_callback_listeners)
    ipc.start_callback_listeners()
    start_comfyui()


@ipc.restrict_to_process('comfyui')
def start_comfyui():
    print('[sd-webui-comfyui]', 'Injecting custom extensions...')
    paths.share_webui_folder_paths()
    patch_comfyui()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    comfyui_main_path = os.getenv('SD_WEBUI_COMFYUI_MAIN')
    runpy.run_path(os.path.join(comfyui_main_path, 'main.py'), {}, '__main__')


@ipc.restrict_to_process('comfyui')
def patch_comfyui():
    custom_extension_injector.register_webui_extensions()
    routes_extension.patch_server_routes()
    queue_tracker.patch_prompt_queue()


if __name__ == '__main__':
    main()
