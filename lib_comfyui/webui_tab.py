import os
import importlib
import sys

import gradio as gr
from modules import shared
import install_comfyui
from lib_comfyui import comfyui_adapter, webui_settings
importlib.reload(install_comfyui)
importlib.reload(comfyui_adapter)
importlib.reload(webui_settings)


def create_tab():
    install_location = webui_settings.get_install_location()
    with gr.Blocks() as tab:
        if os.path.exists(install_location):
            gr.HTML(comfyui_app_html)
        else:
            with gr.Row():
                gr.Markdown(comfyui_install_instructions_markdown)

            with gr.Row():
                with gr.Column():
                    install_button = gr.Button('Install ComfyUI', variant='primary')

                with gr.Column(scale=2):
                    install_path = gr.Textbox(placeholder=f'Leave empty to install at {install_comfyui.default_install_location}')

            with gr.Row():
                installed_feedback = gr.Markdown()

            install_button.click(automatic_install_comfyui, inputs=[install_path], outputs=[installed_feedback], show_progress=True)

    return [(tab, 'ComfyUI', 'comfyui_webui_root')]


def automatic_install_comfyui(install_location):
    install_location = install_location.strip()
    if not install_location:
        install_location = install_comfyui.default_install_location

    if cannot_install_at(install_location):
        message = 'Error! The provided ComfyUI path already exists. Please provide a path to an empty or non-existing directory.'
        print(message, file=sys.stderr)
        return gr.Markdown.update(message)

    install_comfyui.main(install_location)
    shared.opts.comfyui_install_location = install_location

    return gr.Markdown.update('Installed! Now please reload the UI.')


def cannot_install_at(path):
    is_non_empty_dir = os.path.isdir(path) and os.listdir(path)
    return os.path.exists(path) and not is_non_empty_dir


comfyui_install_instructions_markdown = '''
### ComfyUI extension
It looks like your ComfyUI installation isn't set up yet!  
Go to Settings > ComfyUI, and set the proper install location.  

Alternatively, if you don't have a ComfyUI install yet, you can (literally) just clic this button to install it automatically: 
'''


comfyui_app_html = f'''
<div id="comfyui_webui_container">
    <object data="http://127.0.0.1:{shared.cmd_opts.comfyui_port}" id="comfyui_webui_root"></object>
</div>
'''
