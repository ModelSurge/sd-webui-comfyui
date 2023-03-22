import sys
import os
import importlib
from modules import shared
from torch import multiprocessing
from modules import script_callbacks
from lib_comfyui import async_comfyui_loader, webui_settings
importlib.reload(webui_settings)
importlib.reload(async_comfyui_loader)


thread = None


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    model_queue = multiprocessing.Queue()
    start_comfyui_process(model_queue, install_location)

    def on_model_loaded(model):
        model_queue.put(model.sd_model_checkpoint)

    script_callbacks.on_model_loaded(on_model_loaded)
    if shared.sd_model is not None:
        on_model_loaded(shared.sd_model)


def start_comfyui_process(model_queue, install_location):
    global thread
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    try:
        sys.path.insert(0, sys_path_to_add)
        multiprocessing_spawn = multiprocessing.get_context('spawn')
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
