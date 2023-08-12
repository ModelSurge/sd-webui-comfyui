import json
import operator
from typing import Tuple

import gradio as gr
from lib_comfyui import external_code, global_state
from lib_comfyui.webui import gradio_utils, settings
from lib_comfyui.comfyui import iframe_requests


class AccordionInterface:
    def __init__(self, get_elem_id, is_img2img):
        from modules import ui

        self.tab = "img2img" if is_img2img else "txt2img"

        workflow_types = external_code.get_workflow_types(self.tab)
        first_workflow_type = workflow_types[0]
        workflow_type_ids = {
            workflow_type.display_name: workflow_type.get_ids(self.tab)[0]
            for workflow_type in workflow_types
        }

        self.accordion = gr.Accordion(
            label='ComfyUI',
            open=False,
            elem_id=get_elem_id('accordion'),
        )

        self.iframes = gr.HTML(value=self.get_iframes_html(workflow_type_ids[first_workflow_type.display_name]))
        self.enable = gr.Checkbox(
            label='Enable',
            elem_id=get_elem_id('enabled'),
            value=False,
        )
        self.current_workflow_display_name = gr.Dropdown(
            label='Edit workflow type',
            choices=[workflow_type.display_name for workflow_type in workflow_types],
            value=first_workflow_type.display_name,
            elem_id=get_elem_id('displayed_workflow_type'),
        )
        self.queue_front = gr.Checkbox(
            label='Queue front',
            elem_id=get_elem_id('queue_front'),
            value=True,
        )
        self.refresh_button = gr.Button(
            value=f'{ui.refresh_symbol} Reload ComfyUI interfaces (client side)',
            elem_id=get_elem_id('refresh_button'),
        )

        self._rendered = False

    def get_iframes_html(self, first_workflow_type_id: str) -> str:
        comfyui_client_url = settings.get_comfyui_client_url()

        iframes = []
        for workflow_type_id in external_code.get_workflow_type_ids(self.tab):
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

    def get_script_ui_components(self) -> Tuple[gr.components.Component, ...]:
        return self.queue_front,

    def arrange_components(self):
        if self._rendered:
            return

        with self.accordion.render():
            with gr.Row():
                self.iframes.render()

            with gr.Row():
                with gr.Column():
                    self.enable.render()
                    self.current_workflow_display_name.render()

                with gr.Column():
                    self.queue_front.render()
                    self.refresh_button.render()

    def connect_events(self, script):
        if self._rendered:
            return

        self.refresh_button.click(
            fn=None,
            _js='reloadComfyuiIFrames'
        )

        workflow_types = external_code.get_workflow_types(self.tab)
        first_workflow_type = workflow_types[0]
        workflow_type_ids = {
            workflow_type.display_name: workflow_type.get_ids(self.tab)[0]
            for workflow_type in workflow_types
        }

        current_workflow_type_id = gradio_utils.ExtensionDynamicProperty(
            key=f'current_workflow_type_id_{self.tab}',
            value=workflow_type_ids[first_workflow_type.display_name],
        )
        enabled_display_names = gradio_utils.ExtensionDynamicProperty(
            key=f'enabled_display_names_{self.tab}',
            value=[],
        )

        self.current_workflow_display_name.change(
            fn=workflow_type_ids.get,
            inputs=[self.current_workflow_display_name],
            outputs=[current_workflow_type_id],
        )
        current_workflow_type_id.change(
            fn=None,
            _js='changeDisplayedWorkflowType',
            inputs=[current_workflow_type_id],
        )

        self.enable.select(
            fn=lambda enabled_display_names, current_workflow_display_name, enable: list(
                set(enabled_display_names) | {current_workflow_display_name}
                if enable else
                set(enabled_display_names) - {current_workflow_display_name}
            ),
            inputs=[enabled_display_names, self.current_workflow_display_name, self.enable],
            outputs=[enabled_display_names]
        )
        self.current_workflow_display_name.change(
            fn=operator.contains,
            inputs=[enabled_display_names, self.current_workflow_display_name],
            outputs=[self.enable],
        )

        enable_style = gr.HTML()
        for comp in [enabled_display_names, self.current_workflow_display_name]:
            comp.change(
                fn=lambda enabled_display_names, current_workflow_display_name: f'''<style>
                    {f'div#{self.current_workflow_display_name.elem_id} input,' if current_workflow_display_name in enabled_display_names else ''
                    }{','.join(
                        f'div#{self.current_workflow_display_name.elem_id} ul.options > li.item[data-value="{display_name}"]'
                        for display_name in enabled_display_names
                    )} {{
                        color: greenyellow !important;
                        font-weight: bold;
                    }}
                </style>''',
                inputs=[enabled_display_names, self.current_workflow_display_name],
                outputs=[enable_style],
            )

        enabled_display_names.change(
            fn=self.on_enabled_display_names_change,
            inputs=[enabled_display_names],
        )

        workflows_infotext_field = gr.Textbox(visible=False)
        workflows_infotext_field.change(
            fn=self.on_infotext_change,
            inputs=[workflows_infotext_field, self.current_workflow_display_name],
            outputs=[workflows_infotext_field, enabled_display_names, self.enable],
        )
        script.infotext_fields = [(workflows_infotext_field, 'ComfyUI Workflows')]

        self._rendered = True

    def on_enabled_display_names_change(self, enabled_display_names):
        workflow_types = external_code.get_workflow_types(self.tab)
        workflow_type_ids = {
            workflow_type.display_name: workflow_type.get_ids(self.tab)[0]
            for workflow_type in workflow_types
        }

        if not hasattr(global_state, 'enabled_workflow_type_ids'):
            global_state.enabled_workflow_type_ids = {}

        enabled_workflow_type_ids = {
            workflow_type_ids[workflow_type.display_name]: workflow_type.display_name in enabled_display_names
            for workflow_type in workflow_types
        }
        global_state.enabled_workflow_type_ids.update(enabled_workflow_type_ids)

    def on_infotext_change(self, serialized_graphs, current_workflow_display_name):
        if not serialized_graphs:
            return (gr.skip(),) * 3

        if not hasattr(global_state, 'enabled_workflow_type_ids'):
            global_state.enabled_workflow_type_ids = {}

        serialized_graphs = json.loads(serialized_graphs)
        workflow_graphs = {
            workflow_type.get_ids(self.tab)[0]: (
                serialized_graphs.get(workflow_type.base_id, json.loads(workflow_type.default_workflow)),
                workflow_type,
            )
            for workflow_type in global_state.get_workflow_types(self.tab)
        }

        new_enabled_display_names = []
        for workflow_type_id, (graph, workflow_type) in workflow_graphs.items():
            is_custom_workflow = workflow_type.base_id in serialized_graphs
            global_state.enabled_workflow_type_ids[workflow_type_id] = is_custom_workflow
            if is_custom_workflow:
                new_enabled_display_names.append(workflow_type.display_name)
            iframe_requests.set_workflow_graph(graph, workflow_type_id)

        return (
            gr.Textbox.update(value=''),
            gr.update(value=new_enabled_display_names),
            gr.update(value=current_workflow_display_name in new_enabled_display_names),
        )
