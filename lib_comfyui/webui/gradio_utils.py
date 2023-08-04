import gradio as gr
import json
import os
import re
from lib_comfyui import comfyui_context


def ExtensionDynamicProperty(key, value, *, visible=False, **kwargs):
    extension_property = re.sub('[^a-zA-Z0-9_]', '_', os.path.basename(comfyui_context.get_webui_base_dir()))
    return gr.HTML(f'<div {extension_property}_key="{key}">{json.dumps(value)}</div>', visible=visible, **kwargs)
