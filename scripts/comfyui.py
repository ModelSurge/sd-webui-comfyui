import gradio as gr

import modules.scripts as scripts
from lib_comfyui import webui_callbacks, webui_settings, global_state, platform_utils
from comfyui_custom_nodes import webui_postprocess_input, webui_postprocess_output
from lib_comfyui.polling_client import ComfyuiNodeWidgetRequests
from modules import shared, ui_common


class ComfyUIScript(scripts.Script):
    def get_xxx2img_str(self):
        return "img2img" if self.is_img2img else "txt2img"

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
        with gr.Row():
            refresh_button = gr.Button(value=f'{ui_common.refresh_symbol} Reload ComfyUI interface (client side)', elem_id='sd-comfyui-webui-refresh_button')
            refresh_button.click(
                fn=None,
                _js='reloadComfyuiIFrames'
            )
        return queue_front, output_node_label

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def process(self, p, *args):
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return

    def postprocess_batch_list(self, p, pp, queue_front, output_node_label, **kwargs):
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return
        if getattr(shared.state, 'interrupted', False):
            return
        if len(pp.images) == 0:
            return

        batch_results = ComfyuiNodeWidgetRequests.start_workflow_sync(
            batch=pp.images,
            workflow_type='postprocess',
            is_img2img=self.is_img2img,
            required_node_types=webui_postprocess_output.expected_node_types,
            queue_front=queue_front,
        )

        if batch_results is None or 'error' in batch_results:
            return

        batch_size_factor = len(batch_results) // len(pp.images)

        for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
            list_to_scale[:] = list_to_scale * batch_size_factor

        pp.images.clear()
        pp.images.extend(batch_results)


webui_callbacks.register_callbacks()
