import gradio as gr
import json


def ExtensionDynamicProperty(key, value, *, visible=False, **kwargs):
    extension_property = "sd_webui_comfyui"
    return gr.HTML(f'<div {extension_property}_key="{key}">{json.dumps(value)}</div>', visible=visible, **kwargs)
