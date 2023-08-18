import re

import torch

from modules import scripts
from lib_comfyui import global_state, platform_utils, external_code, default_workflow_types, comfyui_process
from lib_comfyui.webui import callbacks, settings, workflow_patcher, gradio_utils, accordion
from lib_comfyui.comfyui import iframe_requests, type_conversion


class ComfyUIScript(scripts.Script):
    def __init__(self):
        # is_img2img is not available here. `accordion` is initialized below, in the is_img2img setter
        self.accordion = None
        self._is_img2img = None

    def title(self):
        return "ComfyUI"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    @property
    def is_img2img(self):
        return self._is_img2img

    @is_img2img.setter
    def is_img2img(self, is_img2img):
        self._is_img2img = is_img2img
        if self.accordion is None:
            # now, we can instantiate the accordion
            self.accordion = accordion.AccordionInterface(self.elem_id, self.get_tab())

    def get_tab(self, is_img2img: bool = None):
        if is_img2img is None:
            is_img2img = self.is_img2img
        return "img2img" if is_img2img else "txt2img"

    def ui(self, is_img2img):
        global_state.is_ui_instantiated = True
        self.accordion.arrange_components()
        self.accordion.connect_events()
        self.accordion.setup_infotext_fields(self)
        return self.accordion.get_script_ui_components()

    def process(self, p, queue_front, enabled_workflow_type_ids, **kwargs):
        if not getattr(global_state, 'enabled', True):
            return

        if not hasattr(global_state, 'enabled_workflow_type_ids'):
            global_state.enabled_workflow_type_ids = {}

        global_state.enabled_workflow_type_ids.update(enabled_workflow_type_ids)

        global_state.queue_front = queue_front
        workflow_patcher.patch_processing(p)

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        if not getattr(global_state, 'enabled', True):
            return
        if len(pp.images) == 0:
            return

        all_results = []
        for batch_input in extract_contiguous_buckets(pp.images, p.batch_size):
            batch_results = external_code.run_workflow(
                workflow_type=default_workflow_types.postprocess_workflow_type,
                tab=self.get_tab(),
                batch_input=type_conversion.webui_image_to_comfyui(torch.stack(batch_input).to('cpu')),
                identity_on_error=True,
            )

            for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
                list_to_scale[:] = list_to_scale * len(batch_results)

            all_results.extend(
                image
                for batch in batch_results
                for image in type_conversion.comfyui_image_to_webui(batch, return_tensors=True))

        pp.images.clear()
        pp.images.extend(all_results)
        iframe_requests.extend_infotext_with_comfyui_workflows(p, self.get_tab())


def extract_contiguous_buckets(images, batch_size):
    current_shape = None
    begin_index = 0

    for i, image in enumerate(images):
        if current_shape is None:
            current_shape = image.size()

        image_has_different_shape = image.size() != current_shape
        batch_is_full = i - begin_index >= batch_size
        is_last_image = i == len(images) - 1

        if image_has_different_shape or batch_is_full or is_last_image:
            end_index = i + 1 if is_last_image else i
            yield images[begin_index:end_index]
            begin_index = i
            current_shape = None


callbacks.register_callbacks()
default_workflow_types.add_default_workflow_types()
settings.init_extension_base_dir()
workflow_patcher.apply_patches()

from modules import generation_parameters_copypaste
generation_parameters_copypaste.re_param_code = r'\s*([\w ]+):\s*("(?:\\.|[^\\"])+"|[^,]*)(?:,|$)'
generation_parameters_copypaste.re_param = re.compile(generation_parameters_copypaste.re_param_code)
