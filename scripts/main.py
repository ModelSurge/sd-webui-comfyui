import modules.scripts as scripts
import sys
import importlib

base_dir = scripts.basedir()
sys.path.append(base_dir)

from lib_comfyui import webui_callbacks
importlib.reload(webui_callbacks)


class ComfyUIScript(scripts.Script):
    def title(self):
        return "ComfyUI"

    def ui(self, is_img2img):
        return []

    def show(self, is_img2img):
        return scripts.AlwaysVisible


webui_callbacks.register_callbacks()
