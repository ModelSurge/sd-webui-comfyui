import sys
import os
import runpy
from modules import shared
import threading


def update_queue(model_queue):
    while True:
        shared.sd_model = model_queue.get()


def main(model_queue):
    threading.Thread(target=update_queue, args=(model_queue, )).start()

    comfyui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ComfyUI')
    # comfyui_path = r'C:\Users\Plads\Documents\GitHub\stable diffusion\ComfyUI'
    sys.path.insert(0, comfyui_path)
    sys.argv = sys.argv[:1]

    runpy.run_path(os.path.join(comfyui_path, "main.py"), {}, '__main__')
