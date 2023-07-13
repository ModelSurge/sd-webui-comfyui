import sys
import os
import importlib
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings
importlib.reload(webui_settings)
importlib.reload(async_comfyui_loader)


thread = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
model_queue = multiprocessing_spawn.Queue()


def on_model_loaded(sd_model):
    sd_model.share_memory()
    state_dict = sd_model.state_dict()
    patched_sd = {}
    for k, v in state_dict.items():
        patched_sd[k] = v.cpu()
    model_queue.put(patched_sd)


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global thread
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    try:
        sys.path.insert(0, sys_path_to_add)
        thread = multiprocessing_spawn.Process(target=async_comfyui_loader.main, args=(model_queue, install_location), daemon=True)
        thread.start()
    finally:
        sys.path.clear()
        sys.path.extend(original_sys_path)


def stop():
    global thread
    if thread is None:
        return

    thread.terminate()
    thread = None
