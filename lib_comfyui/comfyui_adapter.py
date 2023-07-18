import os
from torch import multiprocessing
from lib_comfyui import (
    async_comfyui_loader,
    webui_settings,
    comfyui_requests,
)
from lib_comfyui.comfyui_context import ComfyuiContext
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


def get_comfyui_request_params():
    return {
        'request': '/webui_request_queue_prompt',
        'expectedNodeTypes': shared.expected_node_types if hasattr(shared, 'expected_node_types') else [],
        'queueFront': shared.queue_front if hasattr(shared, 'queue_front') else False,
    }


comfyui_process = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
producers = [
    ProducerHandler(queue=SynchronizingQueue(producer=get_cpu_state_dict, ctx=multiprocessing_spawn)),
    ProducerHandler(queue=SynchronizingQueue(producer=get_opts_outdirs, ctx=multiprocessing_spawn)),
    ProducerHandler(queue=SynchronizingQueue(producer=get_last_output_images, ctx=multiprocessing_spawn)),
    ProducerHandler(queue=SynchronizingQueue(producer=get_comfyui_request_params, ctx=multiprocessing_spawn)),
]


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    [p.start() for p in producers]
    comfyui_requests.init_multiprocess_request_event(ctx=multiprocessing_spawn)
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process

    with ComfyuiContext():
        comfyui_process = multiprocessing_spawn.Process(
            target=async_comfyui_loader.main,
            args=(
                *[p.queue for p in producers], comfyui_requests.mp_event, comfyui_requests.comfyui_prompt_finished_queue,
                install_location),
            daemon=True,
        )
        comfyui_process.start()


def stop():
    stop_comfyui_process()
    [p.stop() for p in producers]


def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None
