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
            gr.Dropdown(label='Workflow type', choices=self.get_workflows(), value='preprocess_latent')
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
            if workflow_id.startswith('preprocess_latent'):
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

    def get_workflows(self, is_img2img: bool = None) -> List[str]:
        suffix = "" if is_img2img is None else "_" + self.get_xxx2img_str(is_img2img)
        workflows = [
            'preprocess_latent',
            'postprocess',
        ]
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

    def postprocess_batch(self, p, queue_front, images: list, batch_number, **kwargs):
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return
        if getattr(shared.state, 'interrupted', False):
            return
        if len(images) == 0:
            return

        batch_results = ComfyuiNodeWidgetRequests.start_workflow_sync(
            batch=images,
            workflow_type='postprocess',
            is_img2img=self.is_img2img,
            required_node_types=[],
            queue_front=queue_front,
        )

        if batch_results is None or 'error' in batch_results:
            return

        batch_size_factor = len(batch_results) // len(images)

        for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
            list_to_scale[:] = list_to_scale * batch_size_factor

        images.clear()
        images.extend(batch_results)


def create_sampler_hijack(name: str, model, original_function):
    sampler = original_function(name, model)
    sampler.sample = functools.partial(sample_hijack, original_function=sampler.sample)
    return sampler


sd_samplers.create_sampler = functools.partial(create_sampler_hijack, original_function=sd_samplers.create_sampler)


def sample_hijack(p, x, *args, original_function, **kwargs):
    if getattr(shared.opts, 'comfyui_enabled', True):
        preprocessed_x = ComfyuiNodeWidgetRequests.start_workflow_sync(
            batch=x.to(device='cpu'),
            workflow_type='preprocess_latent',
            is_img2img=False,
            required_node_types=[],
            queue_front=True,
        )
        x = torch.stack(preprocessed_x).to(device=x.device)

    return original_function(p, x, *args, **kwargs)


# code location: https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/f865d3e11647dfd6c7b2cdf90dde24680e58acd8/modules/processing.py#L666-L667
# PR: https://github.com/AUTOMATIC1111/stable-diffusion-webui/pull/11957
infotext_module = ast.parse("""
def infotext(iteration=0, position_in_batch=0):
    all_prompts = p.all_prompts[:]
    all_negative_prompts = p.all_negative_prompts[:]
    all_seeds = p.all_seeds[:]
    all_subseeds = p.all_subseeds[:]

    # apply changes to generation data
    all_prompts[iteration * p.batch_size:(iteration + 1) * p.batch_size] = p.prompts
    all_negative_prompts[iteration * p.batch_size:(iteration + 1) * p.batch_size] = p.negative_prompts
    all_seeds[iteration * p.batch_size:(iteration + 1) * p.batch_size] = p.seeds
    all_subseeds[iteration * p.batch_size:(iteration + 1) * p.batch_size] = p.subseeds

    # update p.all_negative_prompts in case extensions changed the size of the batch
    # create_infotext below uses it
    old_negative_prompts = p.all_negative_prompts
    p.all_negative_prompts = all_negative_prompts

    try:
        return create_infotext(p, all_prompts, all_seeds, all_subseeds, comments, iteration, position_in_batch)
    finally:
        # restore p.all_negative_prompts in case extensions changed the size of the batch
        p.all_negative_prompts = old_negative_prompts
""")


def highjack_postprocessed_tensor_to_list():
    from modules import processing
    processing.original_sd_webui_comfyui_process_images_inner = processing.process_images_inner
    parsed_module = ast.parse(inspect.getsource(processing.process_images_inner))
    parsed_function = parsed_module.body[0]

    for inner_function in parsed_function.body:
        if isinstance(inner_function, ast.FunctionDef) and inner_function.name == 'infotext':
            inner_function.body[:] = infotext_module.body[0].body
        if isinstance(inner_function, ast.With):
            for inner_with in inner_function.body:
                if not isinstance(inner_with, ast.For):
                    continue
                for inner_for in inner_with.body:
                    if not isinstance(inner_for, ast.If):
                        continue
                    is_postprocess_if = len([exp for exp in inner_for.body if
                                             hasattr(exp, 'value') and hasattr(exp.value, 'func') and hasattr(
                                                 exp.value.func,
                                                 'attr') and exp.value.func.attr == 'postprocess_batch']) == 1
                    if not is_postprocess_if:
                        continue
                    if_statement = inner_for
                    if_statement.body.insert(0, ast.parse('x_samples_ddim = list(x_samples_ddim)').body[0])

    exec(compile(parsed_module, '<string>', 'exec'), processing.__dict__)


highjack_postprocessed_tensor_to_list()
webui_callbacks.register_callbacks()
