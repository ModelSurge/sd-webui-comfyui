import gradio as gr
from modules import scripts, ui
from lib_comfyui import comfyui_context, global_state, platform_utils, external_code, default_workflow_types, comfyui_process
from lib_comfyui.webui import callbacks, settings, workflow_patcher
from lib_comfyui.comfyui import iframe_requests
import functools


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
        self.infotext_fields = []
        global_state.is_ui_instantiated = True
        with gr.Accordion(f"ComfyUI", open=False, elem_id=self.elem_id('accordion')):
            return self.get_alwayson_ui(is_img2img)

    def get_alwayson_ui(self, is_img2img: bool):
        xxx2img = self.get_xxx2img_str(is_img2img)

        with gr.Row():
            queue_front = gr.Checkbox(
                label='Queue front',
                elem_id=self.elem_id('queue_front'),
                value=True,
            )
            workflow_types = external_code.get_workflow_types(xxx2img)
            first_workflow_type = workflow_types[0]
            workflow_type_ids = {
                workflow_type.display_name: workflow_type.get_ids(xxx2img)[0]
                for workflow_type in workflow_types
            }
            workflow_display_name = gr.Dropdown(
                label='Edit workflow type',
                choices=[workflow_type.display_name for workflow_type in workflow_types],
                value=first_workflow_type.display_name,
                elem_id=self.elem_id('displayed_workflow_type'),
            )
            current_workflow_type_id = gr.Text(
                value=workflow_type_ids[first_workflow_type.display_name],
                visible=False,
                interactive=False,
            )
            workflow_display_name.change(
                fn=workflow_type_ids.get,
                inputs=[workflow_display_name],
                outputs=[current_workflow_type_id],
            )
            current_workflow_type_id.change(
                fn=None,
                _js='changeDisplayedWorkflowType',
                inputs=[current_workflow_type_id],
            )

        with gr.Row():
            gr.HTML(value=self.get_iframes_html(is_img2img, workflow_type_ids[first_workflow_type.display_name]))

        with gr.Row():
            refresh_button = gr.Button(
                value=f'{ui.refresh_symbol} Reload ComfyUI interface (client side)',
                elem_id=self.elem_id('refresh_button'),
            )
            refresh_button.click(
                fn=None,
                _js='reloadComfyuiIFrames'
            )

        self.setup_infotext_updates(workflow_types, xxx2img)

        return queue_front,

    def setup_infotext_updates(self, workflow_types, xxx2img):
        for workflow_type in workflow_types:
            textbox = gr.Textbox(visible=False)

            def change_function(serialized_graph, workflow_type):
                if not serialized_graph:
                    return ''

                ids = workflow_type.get_ids(xxx2img)
                if not ids:
                    return ''

                workflow_type_id = ids[0]
                iframe_requests.set_workflow_graph(serialized_graph, workflow_type_id)
                return gr.Textbox.update(value='')

            change_function = functools.partial(change_function, workflow_type=workflow_type)
            textbox.change(change_function, [textbox], [textbox])
            self.infotext_fields.append((textbox, workflow_type.base_id))

    def get_iframes_html(self, is_img2img: bool, first_workflow_type_id: str) -> str:
        comfyui_client_url = settings.get_comfyui_client_url()

        iframes = []
        for workflow_type_id in external_code.get_workflow_type_ids(self.get_xxx2img_str(is_img2img)):
            html_classes = ['comfyui-embedded-widget']
            if workflow_type_id == first_workflow_type_id:
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
        if len(pp.images) == 0:
            return

        batch_results = external_code.run_workflow(
            workflow_type=default_workflow_types.postprocess_workflow_type,
            tab=self.get_xxx2img_str(),
            batch_input=pp.images,
        )

        batch_size_factor = max(1, len(batch_results) // len(pp.images))

        for list_to_scale in [p.prompts, p.negative_prompts, p.seeds, p.subseeds]:
            list_to_scale[:] = list_to_scale * batch_size_factor

        pp.images.clear()
        pp.images.extend(batch_results)

        iframe_requests.extend_infotext_with_comfyui_workflows(p, self.get_xxx2img_str())


callbacks.register_callbacks()
default_workflow_types.add_default_workflow_types()
comfyui_context.init_webui_base_dir()
workflow_patcher.apply_patches()
comfyui_process.restore_webui_sigint_handler()
