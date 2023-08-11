from typing import Any
import gradio as gr
import json


def ExtensionDynamicProperty(key: str, value: Any, *, visible=False, **kwargs):
    extension_property = "sd_webui_comfyui"
    div_begin = f'<div {extension_property}_key="{key}">'
    div_end = '</div>'

    def preprocess(x: Any) -> Any:
        return json.loads(x[len(div_begin):-len(div_end)])

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
