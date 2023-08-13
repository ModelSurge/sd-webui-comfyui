from typing import Any
import gradio as gr
import json


def ExtensionDynamicProperty(value: Any, key: str = None, *, visible=False, **kwargs):
    extension_property = "sd_webui_comfyui"
    if key is not None:
        div_begin = f'<div {extension_property}_key="{key}">'
        div_end = '</div>'
    else:
        div_begin = ''
        div_end = ''

    def preprocess(x: Any) -> Any:
        return json.loads(x[len(div_begin):len(x) - len(div_end)])

    def postprocess(y: str) -> Any:
        return f'{div_begin}{json.dumps(y)}{div_end}'

    component = gr.HTML(
        value=postprocess(value),
        visible=visible,
        **kwargs,
    )
    component.preprocess = preprocess
    component.postprocess = postprocess

    return component
