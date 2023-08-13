import os
import sys
import textwrap
import gradio as gr
import install_comfyui
from lib_comfyui import external_code, ipc
from lib_comfyui.webui import settings, gradio_utils
from lib_comfyui.comfyui import webui_io
from lib_comfyui.default_workflow_types import sandbox_tab_workflow_type


def create_tab():
    install_location = settings.get_install_location()
    with gr.Blocks() as tab:
        if os.path.exists(install_location):
            gr.HTML(get_comfyui_app_html())
        else:
            with gr.Row():
                gr.Markdown(comfyui_install_instructions_markdown)

            with gr.Column():
                with gr.Row():
                    install_path = gr.Textbox(placeholder=f'Leave empty to install at {install_comfyui.default_install_location}', label='Installation path')

                with gr.Row():
                    install_button = gr.Button('Install ComfyUI', variant='primary')

                with gr.Row():
                    installed_feedback = gr.Markdown()

            install_button.click(automatic_install_comfyui, inputs=[install_path], outputs=[installed_feedback], show_progress=True)

        gradio_utils.ExtensionDynamicProperty(
            key='workflow_type_ids',
            value=external_code.get_workflow_type_ids(),
        )
        gradio_utils.ExtensionDynamicProperty(
            key='workflow_type_display_name_map',
            value={
                workflow_type_id: workflow_type.display_name
                for workflow_type in external_code.get_workflow_types()
                for workflow_type_id in workflow_type.get_ids()
            },
        )
        gradio_utils.ExtensionDynamicProperty(
            key='webui_io_node_names',
            value=list(webui_io.NODE_DISPLAY_NAME_MAPPINGS.keys()),
        )
        gradio_utils.ExtensionDynamicProperty(
            key='webui_io_types',
            value={
                workflow_type_id: {
                    'inputs': list(workflow_type.input_types),
                    'outputs': list(workflow_type.output_types),
                }
                for workflow_type in external_code.get_workflow_types()
                for workflow_type_id in workflow_type.get_ids()
            }
        )

    return [(tab, sandbox_tab_workflow_type.display_name, 'comfyui_webui_root')]


@ipc.restrict_to_process('webui')
def automatic_install_comfyui(install_location):
    from modules import shared
    install_location = install_location.strip()
    if not install_location:
        install_location = install_comfyui.default_install_location

    if not can_install_at(install_location):
        message = 'Error! The provided path already exists. Please provide a path to an empty or non-existing directory.'
        print(message, file=sys.stderr)
        return gr.Markdown.update(message)

    install_comfyui.main(install_location)
    shared.opts.comfyui_install_location = install_location

    return gr.Markdown.update('Installed! Now please reload the UI.')


def can_install_at(path):
    is_empty_dir = os.path.isdir(path) and not os.listdir(path)
    return not os.path.exists(path) or is_empty_dir


comfyui_install_instructions_markdown = '''
## ComfyUI extension
It looks like your ComfyUI installation isn't set up yet!  
If you already have ComfyUI installed on your computer, go to `Settings > ComfyUI`, and set the proper install location.  

Alternatively, if you don't have ComfyUI installed, you can install it with this button:
'''


def get_comfyui_app_html():
    return textwrap.dedent(f'''
        <div id="comfyui_webui_container">
            <iframe
                src="{settings.get_comfyui_client_url()}"
                workflow_type_id="{sandbox_tab_workflow_type.get_ids()[0]}">
            </iframe>
        </div>
    ''')
