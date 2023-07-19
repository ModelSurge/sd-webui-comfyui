import gradio as gr

import modules.scripts as scripts
import sys
from lib_comfyui import webui_callbacks, comfyui_requests
from comfyui_custom_nodes import webui_postprocess_input, webui_postprocess_output

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
            output_node_label = gr.Dropdown(label='Workflow type', choices=['postprocess'], value='postprocess')
        return queue_front, output_node_label

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def postprocess(self, p, res, queue_front, output_node_label, **kwargs):
        images = res.images[res.index_of_first_image:]

        for i in range(p.n_iter):
            range_start = i*p.batch_size
            range_end = (i+1)*p.batch_size
            images_batch = images[range_start:range_end]
            webui_postprocess_input.images = images_batch
            results = comfyui_requests.send({
                'request': '/sd-webui-comfyui/webui_request_queue_prompt',
                'requiredNodeTypes': webui_postprocess_output.expected_node_types,
                'queueFront': queue_front,
            })

            if results is None:
                continue

            res.images[res.index_of_first_image + range_start:res.index_of_first_image + range_end] = results


webui_callbacks.register_callbacks()
