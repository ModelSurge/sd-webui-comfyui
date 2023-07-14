import sys
import os
import runpy
from modules import shared
import threading
from lib_comfyui import argv_conversion, custom_extension_injector, webui_resources_sharing


def main(model_name_queue, comfyui_path):
    start_update_loop(model_name_queue)
    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()
    webui_resources_sharing.share_webui_folder_paths()
    custom_extension_injector.register_webui_extensions()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, "main.py"), {}, '__main__')


def start_update_loop(model_state_dict_queue):
    def update_queue():
        while True:
            shared.sd_model_state_dict = model_state_dict_queue.get()

    threading.Thread(target=update_queue, daemon=True).start()
