import os
import gradio as gr
from modules import shared
import install_comfyui
from lib_comfyui import comfyui_adapter


comfyui_install_instructions_markdown = f'''
### ComfyUI extension
It looks like your ComfyUI installation isn't set up yet!  
Go to `settings -> ComfyUI`, and set the proper install location.  
  
Alternatively, if you don't have a ComfyUI install yet, you can (literally) just clic this button to install it automatically: 
'''
comfyui_app_html = f"""
<div id="comfyui_webui_container">
    <object data="http://127.0.0.1:{shared.cmd_opts.comfyui_port}" id="comfyui_webui_root"></object>
</div>
"""


def automatic_install_comfyui():
    install_comfyui.main(install_comfyui.automatic_install_location)
    shared.opts.comfyui_install_location = install_comfyui.automatic_install_location
    comfyui_adapter.start()


def verify_comfyui_installation(comfyui_install_location):
    return os.path.exists(comfyui_install_location)


def generate_gradio_component():
    with gr.Blocks() as tab:
        html_component = gr.HTML(comfyui_app_html)
        default_text = gr.Markdown(comfyui_install_instructions_markdown, visible=False)
        automatic_install_button = gr.Button('Install ComfyUI')
        automatic_install_button.click(automatic_install_comfyui, inputs=[], outputs=[], show_progress=True)
        automatic_install_button.visible = False
        if verify_comfyui_installation(install_comfyui.automatic_install_location):
            shared.opts.comfyui_install_location = install_comfyui.automatic_install_location
        if not verify_comfyui_installation(shared.opts.comfyui_install_location):
            html_component.visible = False
            default_text.visible = True
            automatic_install_button.visible = True

    return [(tab, 'ComfyUI', 'comfyui_webui_root')]
