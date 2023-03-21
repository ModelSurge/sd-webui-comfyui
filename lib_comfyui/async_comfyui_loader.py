import sys
import os
import runpy
import importlib
from modules import shared
import threading
from lib_comfyui import argv_conversion
importlib.reload(argv_conversion)


def main(model_name_queue, comfyui_path):
    start_update_loop(model_name_queue)
    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()
    print(f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, "main.py"), {}, '__main__')


def start_update_loop(model_name_queue):
    def update_queue():
        while True:
            shared.sd_model_ckpt_name = model_name_queue.get()

    threading.Thread(target=update_queue, daemon=True).start()
