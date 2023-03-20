import sys
import os
import importlib
from torch import multiprocessing
from modules import script_callbacks
from lib_comfyui import async_comfyui_loader
importlib.reload(async_comfyui_loader)


thread = None
model_queue = multiprocessing.Queue()


def on_model_loaded(model):
    model_queue.put(model.sd_model_checkpoint)
script_callbacks.on_model_loaded(on_model_loaded)


def start():
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if sys_path_to_add not in sys.path:
        sys.path.insert(0, sys_path_to_add)
    global thread
    thread = multiprocessing.Process(target=async_comfyui_loader.main, args=(model_queue, ), daemon=True)
    thread.start()


def stop():
    global thread
    thread.terminate()
    thread = None
