import dataclasses
import types
import sys
import os
import runpy
from torch import multiprocessing
from lib_comfyui import argv_conversion, custom_extension_injector, webui_resources_sharing


def main(state_dict_queue, send_state_dict_event, comfyui_path):
    sys.modules["webui_process"] = WebuiProcessData(
        state_dict_queue,
        send_state_dict_event,
    )
    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    folder_paths = webui_resources_sharing.get_folder_paths()

    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()

    webui_resources_sharing.share_webui_folder_paths(folder_paths)
    custom_extension_injector.register_webui_extensions()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, "main.py"), {}, '__main__')


@dataclasses.dataclass
class WebuiProcessData(types.ModuleType):
    state_dict_queue: multiprocessing.Queue
    send_state_dict_event: multiprocessing.Event
