import json
import gradio as gr

from modules import shared, scripts, ui
from lib_comfyui import comfyui_context, global_state, platform_utils, external_code, default_workflow_types, ipc
from lib_comfyui.webui import callbacks, settings, workflow_patcher
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
        if not getattr(global_state, 'enabled', True):
            return

        global_state.queue_front = queue_front
        workflow_patcher.patch_processing(p)

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        if not getattr(global_state, 'enabled', True):
            return
        if getattr(shared.state, 'interrupted', False):
            return
        if len(pp.images) == 0:
            return

        batch_results = ComfyuiNodeWidgetRequests.start_workflow_sync(
            input_batch=pp.images,
            workflow_type=default_workflow_types.postprocess_workflow_type,
            tab=self.get_xxx2img_str(),
            queue_front=getattr(global_state, 'queue_front', True),
        )

        batch_size_factor = max(1, len(batch_results) // len(pp.images))

        for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
            list_to_scale[:] = list_to_scale * batch_size_factor

        pp.images.clear()
        pp.images.extend(batch_results)


callbacks.register_callbacks()
default_workflow_types.add_default_workflow_types()
comfyui_context.init_webui_base_dir()
workflow_patcher.apply_patches()
