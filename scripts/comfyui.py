import functools
import json
from pathlib import Path
import gradio as gr
import torch

import modules.scripts as scripts
from lib_comfyui import webui_callbacks, webui_settings, global_state, platform_utils, external_code
from lib_comfyui.polling_client import ComfyuiNodeWidgetRequests
from modules import shared, ui, sd_samplers


def add_default_workflows():
    workflows_dir = Path(scripts.basedir(), 'workflows', 'default')

    workflows = [
        external_code.Workflow(
            base_id='sandbox_tab',
            display_name='Sandbox',
            tabs=(),
        ),
        external_code.Workflow(
            base_id='postprocess',
            display_name='Postprocess',
            default_workflow=workflows_dir / 'postprocess.json',
        ),
        external_code.Workflow(
            base_id='preprocess_latent',
            display_name='Preprocess (latent)',
            tabs='img2img',
            default_workflow=workflows_dir / 'preprocess_latent.json',
        ),
    ]

    for workflow in workflows:
        external_code.add_workflow(workflow)


add_default_workflows()


class ComfyUIScript(scripts.Script):
    def get_xxx2img_str(self, is_img2img: bool = None):
        if is_img2img is None:
            is_img2img = self.is_img2img
        return "img2img" if is_img2img else "txt2img"

    def title(self):
        return "ComfyUI"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        global_state.is_ui_instantiated = True
        with gr.Accordion(f"ComfyUI", open=False, elem_id=self.elem_id('accordion')):
            controls = self.get_alwayson_ui(is_img2img)
        return controls

    def get_alwayson_ui(self, is_img2img: bool):
        xxx2img = self.get_xxx2img_str(is_img2img)

        with gr.Row():
            queue_front = gr.Checkbox(label='Queue front', elem_id=self.elem_id('queue_front'), value=True)
            workflow_display_names = external_code.get_workflow_display_names(xxx2img)
            workflow_type = gr.Dropdown(label='Workflow type', choices=workflow_display_names, value=workflow_display_names[0], elem_id=self.elem_id('workflow_type'))
            workflow_types = dict(zip(workflow_display_names, external_code.get_workflow_ids(xxx2img)))
            workflow_type.change(
                fn=None,
                _js='changeCurrentWorkflow',
                inputs=[gr.Text(json.dumps(workflow_types), interactive=False, visible=False), workflow_type],
            )

        with gr.Row():
            gr.HTML(value=self.get_iframes_html(is_img2img))

        with gr.Row():
            refresh_button = gr.Button(value=f'{ui.refresh_symbol} Reload ComfyUI interface (client side)', elem_id=self.elem_id('refresh_button'))
            refresh_button.click(
                fn=None,
                _js='reloadComfyuiIFrames'
            )

        return queue_front,

    def get_iframes_html(self, is_img2img: bool) -> str:
        comfyui_client_url = webui_settings.get_comfyui_client_url()

        iframes = []
        first_loop = True
        for workflow_id in external_code.get_workflow_ids(self.get_xxx2img_str(is_img2img)):
            html_classes = ['comfyui-embedded-widget']
            if first_loop:
                first_loop = False
                html_classes.append('comfyui-embedded-widget-display')

            iframes.append(f"""
                <iframe
                    src="{comfyui_client_url}"
                    id="{external_code.get_iframe_id(workflow_id)}"
                    class="{' '.join(html_classes)}"
                    style="width:100%; height:500px;">
                </iframe>
            """)

        return f"""
            <div class="comfyui_iframes">
                {''.join(iframes)}
            </div>
        """

    def process(self, p, queue_front, **kwargs):
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return

        p.sample = functools.partial(self.sample_patch, original_function=p.sample)

    def sample_patch(self, *args, original_function, **kwargs):
        return original_function(*args, **kwargs)

    def postprocess_batch_list(self, p, pp, queue_front, batch_number, **kwargs):
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
            required_node_types=[],
            queue_front=queue_front,
        )

        if batch_results is None or 'error' in batch_results:
            return

        batch_size_factor = max(1, len(batch_results) // len(pp.images))

        for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
            list_to_scale[:] = list_to_scale * batch_size_factor

        pp.images.clear()
        pp.images.extend(batch_results)


def create_sampler_hijack(name: str, model, original_function):
    sampler = original_function(name, model)
    sampler.sample_img2img = functools.partial(sample_img2img_hijack, original_function=sampler.sample_img2img)
    return sampler


sd_samplers.create_sampler = functools.partial(create_sampler_hijack, original_function=sd_samplers.create_sampler)


def sample_img2img_hijack(p, x, *args, original_function, **kwargs):
    if getattr(shared.opts, 'comfyui_enabled', True):
        preprocessed_x = ComfyuiNodeWidgetRequests.start_workflow_sync(
            batch=x.to(device='cpu'),
            workflow_type='preprocess_latent',
            is_img2img=True,
            required_node_types=[],
            queue_front=True,
        )
        x = torch.stack(preprocessed_x).to(device=x.device)

    return original_function(p, x, *args, **kwargs)


webui_callbacks.register_callbacks()
