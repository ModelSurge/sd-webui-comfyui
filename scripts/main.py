import gradio as gr
import modules.scripts as scripts
from modules import shared
import sys
from lib_comfyui import webui_callbacks, comfyui_requests

base_dir = scripts.basedir()
sys.path.append(base_dir)


class ComfyUIScript(scripts.Script):
    def title(self):
        return "ComfyUI"

    def ui(self, is_img2img):
        elem_id_tabname = ("img2img" if is_img2img else "txt2img") + "_comfyui"
        with gr.Group(elem_id=elem_id_tabname):
            with gr.Accordion(f"ComfyUI", open=False, elem_id="sd-comfyui-webui"):
                controls = ComfyUIScript.get_alwayson_ui()
        return controls

    @staticmethod
    def get_alwayson_ui():
        with gr.Row():
            queue_front = gr.Checkbox(label='Queue front', elem_id='sd-comfyui-webui-queue_front')
            output_node_label = gr.Dropdown(label='Output node', choices=['postprocess'], value='postprocess')
        return queue_front, output_node_label

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def postprocess_batch(self, p, queue_front, output_node_label, **kwargs):
        images = kwargs.get('images', None)

        if images is None:
            return

        shared.last_output_images = images
        shared.queue_front = queue_front
        shared.expected_node_types = ['WebuiPostprocessOutput']
        results = comfyui_requests.send_request()

        if results is None:
            return

        for i in range(images.shape[0]):
            images[i] = results[i]


webui_callbacks.register_callbacks()
