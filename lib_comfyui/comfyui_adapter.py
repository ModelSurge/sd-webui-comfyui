import sys
import os
import torch
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings, torch_utils
from lib_comfyui.parallel_utils import SynchronizingQueue, ProducerHandler
from modules import shared, devices, sd_models, sd_models_config


def sd_model_getattr(item):
    if item == 'config_path':
        return sd_models_config.find_checkpoint_config(shared.sd_model.state_dict(), sd_models.select_checkpoint())

    res = getattr(shared.sd_model, item)
    res = torch_utils.deep_to(res, 'cpu')
    return res


def sd_model_apply(*args, **kwargs):
    args = torch_utils.deep_to(args, shared.sd_model.device)
    kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
    with devices.autocast(), torch.no_grad():
        res = shared.sd_model.model(*args, **kwargs)
        return res.detach().cpu().share_memory_()


def get_opts():
    return shared.opts.dumpjson()


comfyui_process = None
multiprocessing_spawn = multiprocessing.get_context('spawn')
model_attribute_handler = ProducerHandler(SynchronizingQueue(sd_model_getattr, ctx=multiprocessing_spawn))
shared_opts_handler = ProducerHandler(SynchronizingQueue(get_opts, ctx=multiprocessing_spawn))
model_apply_handler = ProducerHandler(SynchronizingQueue(sd_model_apply, ctx=multiprocessing_spawn))


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    model_attribute_handler.start()
    model_apply_handler.start()
    shared_opts_handler.start()
    start_comfyui_process(install_location)


def start_comfyui_process(install_location):
    global comfyui_process
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    try:
        sys.path.insert(0, sys_path_to_add)
        comfyui_process = multiprocessing_spawn.Process(
            target=async_comfyui_loader.main,
            args=(model_attribute_handler.queue, model_apply_handler.queue, shared_opts_handler.queue, install_location),
            daemon=True,
        )
        comfyui_process.start()
    finally:
        sys.path.clear()
        sys.path.extend(original_sys_path)


def stop():
    stop_comfyui_process()
    model_apply_handler.stop()
    model_attribute_handler.stop()
    shared_opts_handler.stop()


def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    comfyui_process.terminate()
    comfyui_process = None
