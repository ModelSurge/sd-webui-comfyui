import sys
import os
import runpy
from modules import shared
import threading
from lib_comfyui import cmd_opts_map


def main(model_name_queue):
    start_update_loop(model_name_queue)
    start_comfyui()


def start_comfyui():
    comfyui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ComfyUI')
    sys.path.insert(0, comfyui_path)
    set_comfyui_command_args()
    runpy.run_path(os.path.join(comfyui_path, "main.py"), {}, '__main__')


def set_comfyui_command_args():
    sys.argv = sys.argv[:1]
    argv = cmd_opts_map.convert_arguments(shared.cmd_opts)
    sys.argv.extend(argv)


def start_update_loop(model_name_queue):
    def update_queue():
        while True:
            shared.sd_model_ckpt_name = model_name_queue.get()

    threading.Thread(target=update_queue, daemon=True).start()
