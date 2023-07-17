import dataclasses
import json
import types
import sys
import os
import runpy
from lib_comfyui import argv_conversion, custom_extension_injector, webui_resources_sharing, parallel_utils


def main(model_attribute_queue, model_apply_queue, shared_opts_queue, comfyui_path):
    sys.modules["webui_process"] = WebuiProcessModule(
        model_attribute_queue=model_attribute_queue,
        model_apply_queue=model_apply_queue,
        shared_opts_queue=shared_opts_queue,
    )
    start_comfyui(comfyui_path)


def start_comfyui(comfyui_path):
    folder_paths = webui_resources_sharing.get_folder_paths()

    sys.path.insert(0, comfyui_path)
    argv_conversion.set_comfyui_argv()

    webui_resources_sharing.share_webui_folder_paths(folder_paths)
    custom_extension_injector.register_webui_extensions()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, 'main.py'), {}, '__main__')


@dataclasses.dataclass
class WebuiProcessModule(types.ModuleType):
    model_attribute_queue: parallel_utils.SynchronizingQueue
    model_apply_queue: parallel_utils.SynchronizingQueue
    shared_opts_queue: parallel_utils.SynchronizingQueue

    def fetch_model_attribute(self, item):
        return self.model_attribute_queue.get(args=(item,))

    def apply_model(self, *args, **kwargs):
        return self.model_apply_queue.get(args=args, kwargs=kwargs)

    def fetch_shared_opts(self):
        self.shared_opts_queue.put(())
        return types.SimpleNamespace(**json.loads(self.shared_opts_queue.get()))
