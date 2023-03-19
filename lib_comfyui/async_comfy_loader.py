import sys
import os
import runpy
from modules import shared
import threading
from lib_comfyui import argv_conversion


def main(model_name_queue):
    start_update_loop(model_name_queue)
    start_comfyui()


def start_comfyui():
    comfyui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ComfyUI')
    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_command_args()
    runpy.run_path(os.path.join(comfyui_path, "main.py"), {}, '__main__')


def start_update_loop(model_name_queue):
    def update_queue():
        while True:
            shared.sd_model_ckpt_name = model_name_queue.get()

    threading.Thread(target=update_queue, daemon=True).start()
