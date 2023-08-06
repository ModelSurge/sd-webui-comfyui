import atexit
import signal
import os
from torch import multiprocessing
from lib_comfyui import ipc, torch_utils, argv_conversion, parallel_utils
from lib_comfyui.webui import settings
from lib_comfyui.comfyui import pre_main
from lib_comfyui.comfyui_context import ComfyuiContext


comfyui_process = None
multiprocessing_spawn = multiprocessing.get_context('spawn')


@ipc.restrict_to_process('webui')
def start():
    from modules import shared

    install_location = settings.get_install_location()
    if not os.path.exists(install_location):
        return

    if not getattr(shared.opts, 'comfyui_enabled', True):
        return

    ipc.current_process_callback_listeners = {'webui': parallel_utils.CallbackWatcher(ipc.call_fully_qualified, 'webui')}
    ipc.current_process_queues = {'comfyui': parallel_utils.CallbackQueue('comfyui')}
    ipc.start_callback_listeners()
    atexit.register(stop)
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process

    with ComfyuiContext():
        comfyui_process = multiprocessing_spawn.Process(
            target=pre_main.main,
            args=(
                install_location,
                argv_conversion.get_comfyui_args(),
            ),
            daemon=True,
        )
        comfyui_process.start()


def stop():
    atexit.unregister(stop)
    stop_comfyui_process()
    ipc.stop_callback_listeners()


@ipc.restrict_to_process('webui')
def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None


# remove this when comfyui starts using subprocess with an isolated venv
def restore_webui_sigint_handler():
    print('[sd-webui-comfyui]', 'restoring graceful SIGINT handler for the webui process')
    def sigint_handler(sig, frame):
        exit()

    signal.signal(signal.SIGINT, sigint_handler)
