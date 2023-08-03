import functools
import json
import gradio as gr
import torch
import torchvision.transforms.functional

from modules import shared, scripts, ui, sd_samplers, processing
from lib_comfyui import comfyui_context, global_state, platform_utils, external_code, default_workflow_types
from lib_comfyui.webui import callbacks, settings
from lib_comfyui.comfyui.routes_extension import ComfyuiNodeWidgetRequests


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
            return self.get_alwayson_ui(is_img2img)

    def get_alwayson_ui(self, is_img2img: bool):
        xxx2img = self.get_xxx2img_str(is_img2img)

        with gr.Row():
            queue_front = gr.Checkbox(label='Queue front', elem_id=self.elem_id('queue_front'), value=True)
            workflow_type_display_names = external_code.get_workflow_type_display_names(xxx2img)
            workflow_type = gr.Dropdown(label='Displayed workflow type', choices=workflow_type_display_names, value=workflow_type_display_names[0], elem_id=self.elem_id('displayed_workflow_type'))
            workflow_types = dict(zip(workflow_type_display_names, external_code.get_workflow_type_ids(xxx2img)))
            workflow_type.change(
                fn=None,
                _js='changeDisplayedWorkflowType',
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
        comfyui_client_url = settings.get_comfyui_client_url()

        iframes = []
        first_loop = True
        for workflow_type_id in external_code.get_workflow_type_ids(self.get_xxx2img_str(is_img2img)):
            html_classes = ['comfyui-embedded-widget']
            if first_loop:
                first_loop = False
                html_classes.append('comfyui-embedded-widget-display')

            iframes.append(f"""
                <iframe
                    src="{comfyui_client_url}"
                    workflow_type_id="{workflow_type_id}"
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

        p.comfyui_patches = getattr(p, 'comfyui_patches', set())
        if 'sample' not in p.comfyui_patches:
            p.sample = functools.partial(self.p_sample_patch, original_function=p.sample, comfyui_queue_front=queue_front)
            p.comfyui_patches.add('sample')

        if isinstance(p, processing.StableDiffusionProcessingImg2Img) and 'init' not in p.comfyui_patches:
            p.init = functools.partial(self.p_img2img_init, original_function=p.init, p_ref=p, comfyui_queue_front=queue_front)
            p.comfyui_patches.add('init')

    def p_sample_patch(self, *args, original_function, comfyui_queue_front: bool, **kwargs):
        x = original_function(*args, **kwargs)
        if getattr(shared.opts, 'comfyui_enabled', True):
            postprocessed_x = ComfyuiNodeWidgetRequests.start_workflow_sync(
                input_batch=x.to(device='cpu'),
                workflow_type=default_workflow_types.postprocess_latent_workflow_type,
                tab=self.get_xxx2img_str(),
                queue_front=comfyui_queue_front,
            )
            x = torch.stack(postprocessed_x).to(device=x.device)

        return x

    def p_img2img_init(self, *args, original_function, p_ref: processing.StableDiffusionProcessingImg2Img, comfyui_queue_front: bool, **kwargs):
        if getattr(shared.opts, 'comfyui_enabled', True):
            preprocessed_images = ComfyuiNodeWidgetRequests.start_workflow_sync(
                input_batch=[torchvision.transforms.functional.pil_to_tensor(image) for image in p_ref.init_images],
                workflow_type=default_workflow_types.preprocess_workflow_type,
                tab='img2img',
                queue_front=comfyui_queue_front,
            )
            p_ref.init_images = [torchvision.transforms.functional.to_pil_image(image) for image in preprocessed_images]

        return original_function(*args, **kwargs)

    def postprocess_batch_list(self, p, pp, queue_front, batch_number, **kwargs):
        if not getattr(shared.opts, 'comfyui_enabled', True):
            return
        if getattr(shared.state, 'interrupted', False):
            return
        if len(pp.images) == 0:
            return

        batch_results = ComfyuiNodeWidgetRequests.start_workflow_sync(
            input_batch=pp.images,
            workflow_type=default_workflow_types.postprocess_workflow_type,
            tab=self.get_xxx2img_str(),
            queue_front=queue_front,
        )

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
            input_batch=x.to(device='cpu'),
            workflow_type=default_workflow_types.preprocess_latent_workflow_type,
            tab='img2img',
            queue_front=True,
        )
        x = torch.stack(preprocessed_x).to(device=x.device)

    return original_function(p, x, *args, **kwargs)


callbacks.register_callbacks()
default_workflow_types.add_default_workflow_types()
comfyui_context.init_webui_base_dir()
