import modules.scripts as scripts
import sys
import gradio as gr

base_dir = scripts.basedir()
sys.path.append(base_dir)

from modules import script_callbacks
from lib_comfyui import comfy_adapter


class ComfyUIScript(scripts.Script):
    def title(self):
        return "ComfyUI"

    def ui(self, is_img2img):
        return []

    def show(self, is_img2img):
        return scripts.AlwaysVisible


def on_ui_tabs():
    root = gr.HTML(f"""<div id="comfyui_webui_container"><object data="http://127.0.0.1:7861" id="comfyui_webui_root"></object></div>""")
    return [(root, 'ComfyUI', 'comfyui_webui_root')]


def on_app_started(*_):
    comfy_adapter.start()


def on_script_unloaded(*_):
    comfy_adapter.stop()


script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_app_started(on_app_started)
script_callbacks.on_script_unloaded(on_script_unloaded)
