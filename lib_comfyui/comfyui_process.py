import atexit
import os
import threading

from torch import multiprocessing
from lib_comfyui import ipc, torch_utils, argv_conversion
from lib_comfyui.webui import settings, paths
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

    ipc.reset_state()
    ipc.start_callback_listeners()
    atexit.register(ipc.stop_callback_listeners)
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process

    with ComfyuiContext():
        comfyui_process = multiprocessing_spawn.Process(
            target=pre_main.main,
            args=(
                install_location,
                paths.get_folder_paths(),
                {**ipc.get_current_process_queues(), **ipc.current_process_queues},
                argv_conversion.get_comfyui_args(),
            ),
            daemon=True,
        )
        comfyui_process.start()


def stop():
    stop_comfyui_process()
    ipc.stop_callback_listeners()
    atexit.unregister(ipc.stop_callback_listeners)


@ipc.restrict_to_process('webui')
def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None
