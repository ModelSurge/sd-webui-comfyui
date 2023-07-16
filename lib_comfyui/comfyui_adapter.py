import sys
import os
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings
from lib_comfyui.parallel_utils import StoppableThread, SynchronizingQueue
from modules import shared


def get_cpu_state_dict():
    return unwrap_cpu_state_dict(shared.sd_model.state_dict())


def unwrap_cpu_state_dict(state_dict: dict) -> dict:
    model_key_prefixes = ('cond_stage_model', 'first_stage_model', 'model.diffusion_model')
    return {
        k.replace('.wrapped.', '.'): v.cpu().share_memory_()
        for k, v in state_dict.items()
        if k.startswith(model_key_prefixes)
    }


comfyui_process = None
state_dict_thread = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
state_dict_queue = SynchronizingQueue(get_cpu_state_dict, ctx=multiprocessing_spawn)


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    start_state_dict_thread()
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    try:
        sys.path.insert(0, sys_path_to_add)
        comfyui_process = multiprocessing_spawn.Process(
            target=async_comfyui_loader.main,
            args=(state_dict_queue, install_location),
            daemon=True,
        )
        comfyui_process.start()
    finally:
        sys.path.clear()
        sys.path.extend(original_sys_path)


def start_state_dict_thread():
    global state_dict_thread

    def thread_loop():
        global state_dict_thread, state_dict_queue
        while state_dict_thread.is_running():
            state_dict_queue.attend_consumer(timeout=1)

    state_dict_thread = StoppableThread(target=thread_loop, daemon=True)
    state_dict_thread.start()


def stop():
    stop_comfyui_process()
    stop_state_dict_thread()


def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None


def stop_state_dict_thread():
    global state_dict_thread, state_dict_queue
    if state_dict_thread is None:
        return

    state_dict_thread.join()
    state_dict_thread = None
