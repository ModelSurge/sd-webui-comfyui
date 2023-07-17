import dataclasses
import json
import types
import sys
import os
import runpy
from torch import multiprocessing
from lib_comfyui import argv_conversion, custom_extension_injector, webui_resources_sharing, queue_prompt_button


def main(
        state_dict_queue,
        shared_opts_queue,
        output_images_queue,
        batch_count_gueue,
        queue_prompt_button_event,
        comfyui_path
):
    sys.modules["webui_process"] = WebuiProcessModule(
        state_dict_queue=state_dict_queue,
        shared_opts_queue=shared_opts_queue,
        output_images_queue=output_images_queue,
        batch_count_gueue=batch_count_gueue,
        queue_prompt_button_event=queue_prompt_button_event,
    )
    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    folder_paths = webui_resources_sharing.get_folder_paths()

    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()

    webui_resources_sharing.share_webui_folder_paths(folder_paths)
    custom_extension_injector.register_webui_extensions()
    queue_prompt_button.patch_server_routes()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, 'main.py'), {}, '__main__')


@dataclasses.dataclass
class WebuiProcessModule(types.ModuleType):
    state_dict_queue: multiprocessing.Queue
    shared_opts_queue: multiprocessing.Queue
    output_images_queue: multiprocessing.Queue
    batch_count_gueue: multiprocessing.Queue
    queue_prompt_button_event: multiprocessing.Event

    def fetch_model_state_dict(self):
        return self.state_dict_queue.get()

    def fetch_shared_opts(self):
        return types.SimpleNamespace(**json.loads(self.shared_opts_queue.get()))

    def fetch_last_output_images(self):
        return self.output_images_queue.get()

    def fetch_last_batch_count(self):
        return self.batch_count_gueue.get()

    def queue_prompt_button_wait(self):
        self.queue_prompt_button_event.wait()
        self.queue_prompt_button_event.clear()
