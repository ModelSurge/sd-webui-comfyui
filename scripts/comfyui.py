from modules import scripts
from lib_comfyui import global_state, platform_utils, external_code, default_workflow_types, comfyui_process
from lib_comfyui.webui import callbacks, settings, workflow_patcher, gradio_utils, accordion
from lib_comfyui.comfyui import iframe_requests


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
            self.accordion = accordion.AccordionInterface(self.elem_id, is_img2img)

    def get_xxx2img_str(self, is_img2img: bool = None):
        if is_img2img is None:
            is_img2img = self.is_img2img
        return "img2img" if is_img2img else "txt2img"

    def ui(self, is_img2img):
        global_state.is_ui_instantiated = True
        self.accordion.arrange_components()
        self.accordion.connect_events()
        self.accordion.setup_infotext_fields(self)
        return self.accordion.get_script_ui_components()

    def process(self, p, queue_front, **kwargs):
        if not getattr(global_state, 'enabled', True):
            return

        global_state.queue_front = queue_front
        workflow_patcher.patch_processing(p)

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        if not getattr(global_state, 'enabled', True):
            return
        if len(pp.images) == 0:
            return

        batch_results = external_code.run_workflow(
            workflow_type=default_workflow_types.postprocess_workflow_type,
            tab=self.get_xxx2img_str(),
            batch_input=list(pp.images),
        )

        batch_size_factor = max(1, len(batch_results) // len(pp.images))

        for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
            list_to_scale[:] = list_to_scale * batch_size_factor

        pp.images.clear()
        pp.images.extend(batch_results)

        iframe_requests.extend_infotext_with_comfyui_workflows(p, self.get_xxx2img_str())


callbacks.register_callbacks()
default_workflow_types.add_default_workflow_types()
settings.init_extension_base_dir()
workflow_patcher.apply_patches()
