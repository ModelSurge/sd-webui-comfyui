import modules.scripts as scripts
import sys

base_dir = scripts.basedir()
sys.path.append(base_dir)

from modules import script_callbacks
from lib_comfyui import comfyui_adapter
from lib_comfyui import comfyui_tab
from lib_comfyui import comfyui_settings


class ComfyUIScript(scripts.Script):
    def title(self):
        return "ComfyUI"

    def ui(self, is_img2img):
        return []

    def show(self, is_img2img):
        return scripts.AlwaysVisible


def on_ui_tabs():
    return comfyui_tab.generate_gradio_component()


def on_ui_settings():
    return comfyui_settings.add_settings()


def on_app_started(*_):
    comfyui_adapter.start()


def on_script_unloaded(*_):
    comfyui_adapter.stop()


script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_app_started(on_app_started)
script_callbacks.on_script_unloaded(on_script_unloaded)
