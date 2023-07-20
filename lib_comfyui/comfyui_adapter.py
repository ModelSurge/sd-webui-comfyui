import os
from torch import multiprocessing
from lib_comfyui import (
    async_comfyui_loader,
    webui_settings,
)
from lib_comfyui.comfyui_requests import WebuiNodeWidgetRequests
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


comfyui_process = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
producers = [
    ProducerHandler(queue=SynchronizingQueue(producer=get_cpu_state_dict, ctx=multiprocessing_spawn)),
    ProducerHandler(queue=SynchronizingQueue(producer=get_opts_outdirs, ctx=multiprocessing_spawn)),
]


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    [p.start() for p in producers]
    WebuiNodeWidgetRequests.init(multiprocessing_spawn)
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process
    with ComfyuiContext():
        comfyui_process = multiprocessing_spawn.Process(
            target=async_comfyui_loader.main,
            args=(
                *[p.queue for p in producers], *WebuiNodeWidgetRequests.get_queues(),
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
