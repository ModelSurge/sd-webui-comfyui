import dataclasses
import json
import types
import sys
import os
import runpy
from torch import multiprocessing
from lib_comfyui import argv_conversion, custom_extension_injector, webui_resources_sharing, comfyui_requests
from lib_comfyui.comfyui_requests import ComfyuiNodeWidgetRequests

def main(
        state_dict_queue,
        shared_opts_queue,
        start_comfyui_queue,
        finished_comfyui_queue,
        comfyui_path
):
    sys.modules["webui_process"] = WebuiProcessModule(
        state_dict_queue=state_dict_queue,
        shared_opts_queue=shared_opts_queue,
    )

    ComfyuiNodeWidgetRequests.init(start_comfyui_queue, finished_comfyui_queue)
    ComfyuiNodeWidgetRequests.start_listener()

    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    folder_paths = webui_resources_sharing.get_folder_paths()

    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()

    webui_resources_sharing.share_webui_folder_paths(folder_paths)
    print('[sd-webui-comfyui]', 'Injecting custom extensions...')
    patch_comfyui()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, 'main.py'), {}, '__main__')


def patch_comfyui():
    custom_extension_injector.register_webui_extensions()
    comfyui_requests.patch_server_routes()


@dataclasses.dataclass
class WebuiProcessModule(types.ModuleType):
    state_dict_queue: multiprocessing.Queue
    shared_opts_queue: multiprocessing.Queue

    def fetch_model_state_dict(self):
        return self.state_dict_queue.get()

    def fetch_shared_opts(self):
        return types.SimpleNamespace(**json.loads(self.shared_opts_queue.get()))
