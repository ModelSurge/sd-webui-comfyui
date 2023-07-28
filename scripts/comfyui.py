import functools
from typing import List
import gradio as gr

import ast
import inspect

import torch

import modules.scripts as scripts
from lib_comfyui import webui_callbacks, webui_settings, global_state, platform_utils
from lib_comfyui.polling_client import ComfyuiNodeWidgetRequests
from modules import shared, sd_samplers


class ComfyUIScript(scripts.Script):
    def get_xxx2img_str(self, is_img2img: bool = None):
        if is_img2img is None:
            is_img2img = self.is_img2img
        return "img2img" if is_img2img else "txt2img"

    def title(self):
        return "ComfyUI"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img: bool):
        elem_id_tabname = f"{self.get_xxx2img_str(is_img2img)}_comfyui"
        with gr.Group(elem_id=elem_id_tabname):
            with gr.Accordion(f"ComfyUI", open=False, elem_id="sd-comfyui-webui"):
                controls = self.get_alwayson_ui(is_img2img)
        return controls

    def get_alwayson_ui(self, is_img2img: bool):
        with gr.Row():
            queue_front = gr.Checkbox(label='Queue front', elem_id='sd-comfyui-webui-queue_front', value=True)
            gr.Dropdown(label='Workflow type', choices=self.get_workflows(is_img2img, tab_specific=False), value='preprocess_latent' if is_img2img else 'postprocess')
        with gr.Row():
            if not platform_utils.is_unsupported_platform():
                gr.HTML(value=self.get_iframes_html(is_img2img))
            else:
                gr.Label('Your platform does not support this feature yet.')
        return queue_front,

    def get_iframes_html(self, is_img2img: bool) -> str:
        iframes_html = ""
        comfyui_client_url = webui_settings.get_comfyui_client_url()
        for workflow_id in self.get_workflows(is_img2img):
            html_classes = ['comfyui-embedded-widget']
            if (is_img2img and workflow_id.startswith('preprocess_latent')) or (not is_img2img and workflow_id.startswith('postprocess')):
                html_classes.append('comfyui-embedded-widget-display')
            iframes_html += f"""
                <iframe
                    src="{comfyui_client_url}"
                    id="comfyui_{workflow_id}"
                    class="{' '.join(html_classes)}"
                    style="width:100%; height:500px;">
                </iframe>
            """
        return f"""
            <div id="comfyui_iframes">
                {iframes_html}
            </div>
        """

    def get_workflows(self, is_img2img: bool, tab_specific: bool = True) -> List[str]:
        suffix = "" if is_img2img is None else "_" + self.get_xxx2img_str(is_img2img)
        workflows = [
            'postprocess',
        ]
        if is_img2img:
            workflows += (
                'preprocess_latent',
            )
        if tab_specific:
            workflows = [
                workflow + suffix
                for workflow
                in workflows
            ]
        return workflows

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
