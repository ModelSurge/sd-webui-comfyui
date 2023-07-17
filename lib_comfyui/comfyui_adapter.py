import sys
import os
import torch
from torch import multiprocessing
from lib_comfyui import async_comfyui_loader, webui_settings
from lib_comfyui.parallel_utils import SynchronizingQueue, ProducerHandler
from modules import shared, devices


def sd_model_getattr(item):
    res = getattr(shared.sd_model, item)
    if isinstance(res, torch.Tensor):
        res = res.cpu()

    return res


def sd_model_apply(*args, **kwargs):
    args = list(args)

    for i, arg in enumerate(args):
        if isinstance(arg, torch.Tensor):
            args[i] = arg.to(device=shared.sd_model.device, dtype=shared.sd_model.dtype)

    for k, v in kwargs.items():
        if isinstance(v, torch.Tensor):
            kwargs[k] = v.to(device=shared.sd_model.device, dtype=shared.sd_model.dtype)
        elif isinstance(v, list):
            for i, vv in enumerate(v):
                if isinstance(vv, torch.Tensor):
                    v[i] = vv.to(device=shared.sd_model.device, dtype=shared.sd_model.dtype)

    with devices.autocast(), torch.no_grad():
        return shared.sd_model.model(*args, **kwargs).cpu()


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
