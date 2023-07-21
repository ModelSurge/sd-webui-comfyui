import gradio as gr

import modules.scripts as scripts
from lib_comfyui import webui_callbacks, webui_settings, global_state
from comfyui_custom_nodes import webui_postprocess_input, webui_postprocess_output
from lib_comfyui.polling_client import ComfyuiNodeWidgetRequests
from modules import shared


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
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return

        images = res.images[res.index_of_first_image:]
        results = res.images[:res.index_of_first_image]
        initial_amount_of_images = len(images)
        for i in range(p.n_iter):
            range_start = i*p.batch_size
            range_end = (i+1)*p.batch_size
            images_batch = images[range_start:range_end]
            batch_results = ComfyuiNodeWidgetRequests.start_workflow_sync(
                batch=images_batch,
                workflow_type='postprocess',
                is_img2img=self.is_img2img,
                required_node_types=webui_postprocess_output.expected_node_types,
                queue_front=queue_front,
            )

            if batch_results is None or 'error' in batch_results:
                continue

            results.extend(batch_results)

        batch_count_multiplier = (len(results) - res.index_of_first_image) // initial_amount_of_images
        p.n_iter = p.n_iter * batch_count_multiplier
        res.images = results


webui_callbacks.register_callbacks()
