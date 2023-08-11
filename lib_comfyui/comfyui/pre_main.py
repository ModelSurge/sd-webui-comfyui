import atexit
import builtins
import signal
import sys
import os
import runpy
from lib_comfyui import (
    custom_extension_injector,
    ipc,
)
from lib_comfyui.comfyui import routes_extension, queue_tracker
from lib_comfyui.webui import paths, settings


original_print = builtins.print
def comfyui_print(*args, **kwargs):
    return original_print('[ComfyUI]', *args, **kwargs)


@ipc.restrict_to_process('comfyui')
def main():
    builtins.print = comfyui_print
    fix_path()
    setup_ipc()
    patch_comfyui()
    start_comfyui()


@ipc.restrict_to_process('comfyui')
def fix_path():
    def make_path_unique():
        path = sys.path.copy()
        sys.path.clear()
        seen = set()
        sys.path.extend(
            p for p in path
            if not (p in seen or seen.add(p))
        )

    def move_comfyui_to_front():
        comfyui_dir = os.getcwd()
        try:
            sys.path.remove(comfyui_dir)
        except ValueError:
            pass
        sys.path.insert(0, comfyui_dir)

    make_path_unique()
    move_comfyui_to_front()


@ipc.restrict_to_process('comfyui')
def setup_ipc():
    print('[sd-webui-comfyui]', 'Setting up IPC...')
    ipc_strategy_class_name = os.getenv('SD_WEBUI_COMFYUI_IPC_STRATEGY_CLASS_NAME')
    print('[sd-webui-comfyui]', f'Using inter-process communication strategy: {settings.ipc_display_names[ipc_strategy_class_name]}')
    ipc_strategy_factory = getattr(ipc.strategies, os.getenv('SD_WEBUI_COMFYUI_IPC_STRATEGY_CLASS_NAME'))
    ipc.current_callback_listeners = {'comfyui': ipc.callback.CallbackWatcher(ipc.call_fully_qualified, 'comfyui', ipc_strategy_factory)}
    ipc.current_callback_proxies = {'webui': ipc.callback.CallbackProxy('webui', ipc_strategy_factory)}
    ipc.start_callback_listeners()
    atexit.register(ipc.stop_callback_listeners)

    def exit_signal_handler(sig, frame):
        exit()

    # signal handlers for graceful termination
    # they should trigger in one of the following situations:
    # - the user hits ctrl+C
    # linux only:
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
