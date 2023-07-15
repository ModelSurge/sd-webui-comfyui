import sys
import os
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings


thread = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
model_queue = multiprocessing_spawn.Queue()


def on_model_loaded(sd_model):
    sd_model.share_memory()
    state_dict = unwrap_cpu_state_dict(sd_model.state_dict())
    model_queue.put(state_dict)


def unwrap_cpu_state_dict(state_dict: dict) -> dict:
    model_keys = ('cond_stage_model', 'first_stage_model', 'model.diffusion_model')
    return {
        k.replace('.wrapped.', '.'): v.cpu()
        for k, v in state_dict.items()
        if k.startswith(model_keys)
    }


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
