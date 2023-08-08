import atexit
import builtins
import signal
import sys
import os
import runpy
from lib_comfyui import (
    custom_extension_injector,
    ipc,
    ipc_callback,
)
from lib_comfyui.comfyui import routes_extension, queue_tracker
from lib_comfyui.webui import paths


original_print = builtins.print
def comfyui_print(*args, **kwargs):
    return original_print('[ComfyUI]', *args, **kwargs)


@ipc.restrict_to_process('comfyui')
def main():
    builtins.print = comfyui_print
    setup_ipc()
    patch_comfyui()
    start_comfyui()


@ipc.restrict_to_process('comfyui')
def setup_ipc():
    print('[sd-webui-comfyui]', 'Setting up IPC...')
    ipc.current_callback_listeners = {'comfyui': ipc_callback.CallbackWatcher(ipc.call_fully_qualified, 'comfyui')}
    ipc.current_callback_proxies = {'webui': ipc_callback.CallbackProxy('webui')}
    ipc.start_callback_listeners()
    atexit.register(ipc.stop_callback_listeners)

    def exit_signal_handler(sig, frame):
        exit()

    # signal handlers for linux. Windows does not handle these
    # they should trigger in one of the following situations:
    # - the user hits ctrl+C
    # - the webui gradio UI is reloaded
    # - the comfyui server is closed using the stop function of the lib_comfyui.comfyui_process module
    signal.signal(signal.SIGTERM, exit_signal_handler)
    signal.signal(signal.SIGINT, exit_signal_handler)


@ipc.restrict_to_process('comfyui')
def patch_comfyui():
    print('[sd-webui-comfyui]', 'Patching ComfyUI...')
    paths.share_webui_folder_paths()
    custom_extension_injector.register_webui_extensions()
    routes_extension.patch_server_routes()
    queue_tracker.patch_prompt_queue()


@ipc.restrict_to_process('comfyui')
def start_comfyui():
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(os.getcwd(), 'main.py'), {'comfyui_print': comfyui_print}, '__main__')


if __name__ == '__main__':
    ipc.current_process_id = 'comfyui'
    main()
