import sys
import os
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings, queue_prompt_button
from lib_comfyui.parallel_utils import SynchronizingQueue, ProducerHandler
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


def get_opts_outdirs():
    return shared.opts.dumpjson()


def get_last_output_images():
    if hasattr(shared, 'last_output_images'):
        return shared.last_output_images
    return []


def get_last_batch_length():
    if hasattr(shared, 'last_batch_length'):
        return shared.last_batch_length
    return 0


comfyui_process = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
producers = [
    ProducerHandler(queue=SynchronizingQueue(producer=get_cpu_state_dict, ctx=multiprocessing_spawn)),
    ProducerHandler(queue=SynchronizingQueue(producer=get_opts_outdirs, ctx=multiprocessing_spawn)),
    ProducerHandler(queue=SynchronizingQueue(producer=get_last_output_images, ctx=multiprocessing_spawn)),
]


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    [p.start() for p in producers]
    queue_prompt_button.init_multiprocess_button_event(ctx=multiprocessing_spawn)
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    try:
        sys.path.insert(0, sys_path_to_add)
        comfyui_process = multiprocessing_spawn.Process(
            target=async_comfyui_loader.main,
            args=(*[p.queue for p in producers], queue_prompt_button.mp_event, install_location),
            daemon=True,
        )
        comfyui_process.start()
    finally:
        sys.path.clear()
        sys.path.extend(original_sys_path)


def stop():
    stop_comfyui_process()
    [p.stop() for p in producers]


def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None
