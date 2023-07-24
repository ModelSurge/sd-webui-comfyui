import gradio as gr

import functools

from modules import processing
import ast
import inspect

import modules.scripts as scripts
from lib_comfyui import webui_callbacks, webui_settings, global_state, platform_utils
from comfyui_custom_nodes import webui_postprocess_input, webui_postprocess_output
from lib_comfyui.polling_client import ComfyuiNodeWidgetRequests
from modules import shared


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
            if not platform_utils.is_unsupported_platform():
                gr.HTML(value=f"""
                    <iframe src="{webui_settings.get_comfyui_client_url()}" id="comfyui_postprocess_{xxx2img}" class="comfyui-embedded-widget" style="width:100%; height:500px;"></iframe>
                """)
            else:
                gr.Label('Your platform does not support this feature yet.')
        return queue_front, output_node_label

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def process(self, p, *args):
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return

        self.outpath_samples = p.outpath_samples

    def postprocess_batch(self, p, queue_front, output_node_label, images: list, batch_number, **kwargs):
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
            required_node_types=webui_postprocess_output.expected_node_types,
            queue_front=queue_front,
        )

        if batch_results is None or 'error' in batch_results:
            return
            
        images.clear()
        images.extend(batch_results)


original_create_infotext = processing.create_infotext


def patched_create_infotext(p, all_prompts, all_seeds, all_subseeds, comments=None, iteration=0, position_in_batch=0):
    n = iteration
    all_prompts = p.all_prompts[:]
    all_seeds = p.all_seeds[:]
    all_subseeds = p.all_subseeds[:]

    # apply changes to generation data
    all_prompts[n * p.batch_size:(n + 1) * p.batch_size] = p.prompts
    all_seeds[n * p.batch_size:(n + 1) * p.batch_size] = p.seeds
    all_subseeds[n * p.batch_size:(n + 1) * p.batch_size] = p.subseeds

    # update p.all_negative_prompts in case extensions changed the size of the batch
    # create_infotext below uses it
    old_negative_prompts = p.all_negative_prompts[n * p.batch_size:(n + 1) * p.batch_size]
    p.all_negative_prompts[n * p.batch_size:(n + 1) * p.batch_size] = p.negative_prompts

    try:
        return original_create_infotext(p, all_prompts, all_seeds, all_subseeds, comments=comments, iteration=iteration, position_in_batch=position_in_batch)
    finally:
        # restore p.all_negative_prompts in case extensions changed the size of the batch
        p.all_negative_prompts[n * p.batch_size:n * p.batch_size + len(p.negative_prompts)] = old_negative_prompts


processing.create_infotext = patched_create_infotext


def highjack_postprocessed_tensor_to_list():
    from modules import processing
    parsed_module = ast.parse(inspect.getsource(processing.process_images_inner))
    parsed_function = parsed_module.body[0]

    for inner_function in parsed_function.body:
        if not isinstance(inner_function, ast.With):
            continue
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
