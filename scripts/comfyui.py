import gradio as gr

import modules.scripts as scripts
import sys
from lib_comfyui import webui_callbacks, webui_settings, global_state
from comfyui_custom_nodes import webui_postprocess_input, webui_postprocess_output
from lib_comfyui.polling_client import ComfyuiNodeWidgetRequests
from lib_comfyui.queue_tracker import PromptQueueTracker

base_dir = scripts.basedir()
sys.path.append(base_dir)


class ComfyUIScript(scripts.Script):
    def title(self):
        return "ComfyUI"

    def ui(self, is_img2img):
        xxx2img = ("img2img" if is_img2img else "txt2img")
        elem_id_tabname = xxx2img + "_comfyui"
        with gr.Group(elem_id=elem_id_tabname):
            with gr.Accordion(f"ComfyUI", open=False, elem_id="sd-comfyui-webui"):
                controls = ComfyUIScript.get_alwayson_ui(xxx2img)
        return controls

    @staticmethod
    def get_alwayson_ui(xxx2img):
        with gr.Row():
            queue_front = gr.Checkbox(label='Queue front', elem_id='sd-comfyui-webui-queue_front', value=True)
            output_node_label = gr.Dropdown(label='Workflow type', choices=['postprocess'], value='postprocess')
        with gr.Row():
            gr.HTML(value=f"""
                <iframe src="{webui_settings.get_comfyui_client_url()}" id="comfyui_postprocess_{xxx2img}" class="comfyui-embedded-widget" style="width:100%; height:500px;"></iframe>
            """)
        return queue_front, output_node_label

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def postprocess(self, p, res, queue_front, output_node_label, **kwargs):
        images = res.images[res.index_of_first_image:]
        for i in range(p.n_iter):
            range_start = i*p.batch_size
            range_end = (i+1)*p.batch_size
            images_batch = images[range_start:range_end]
            image_results = ComfyuiNodeWidgetRequests.start_workflow_sync(
                batch=images_batch,
                workflow_type='postprocess',
                is_img2img=self.is_img2img,
                required_node_types=webui_postprocess_output.expected_node_types,
                queue_front=queue_front,
            )

            if image_results is None or 'error' in image_results:
                continue

            res.images[res.index_of_first_image + range_start:res.index_of_first_image + range_end] = image_results


webui_callbacks.register_callbacks()
