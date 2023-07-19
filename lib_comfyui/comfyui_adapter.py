import sys
import os
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings, ipc, torch_utils, webui_proxies


comfyui_process = None
multiprocessing_spawn = multiprocessing.get_context('spawn')


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    ipc.start_process_queues()
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    try:
        sys.path.insert(0, sys_path_to_add)
        comfyui_process = multiprocessing_spawn.Process(
            target=async_comfyui_loader.main,
            args=(
                install_location,
                ipc.get_process_queues()
            ),
            daemon=True,
        )
        comfyui_process.start()
    finally:
        sys.path.clear()
        sys.path.extend(original_sys_path)


def stop():
    stop_comfyui_process()
    ipc.stop_process_queues()


def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None
