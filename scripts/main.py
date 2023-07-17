import gradio as gr
import modules.scripts as scripts
from modules import shared
import sys
from lib_comfyui import webui_callbacks, queue_prompt_button

base_dir = scripts.basedir()
sys.path.append(base_dir)


class ComfyUIScript(scripts.Script):
    def title(self):
        return "ComfyUI"

    def ui(self, is_img2img):
        elem_id_tabname = ("img2img" if is_img2img else "txt2img") + "_comfyui"
        with gr.Group(elem_id=elem_id_tabname):
            with gr.Accordion(f"ComfyUI", open=False, elem_id="sd-comfyui-webui"):
                controls = ComfyUIScript.get_alwayson_ui()
        return controls

    @staticmethod
    def get_alwayson_ui():
        with gr.Row():
            run_comfyui_after_generation = gr.Checkbox(label='Run ComfyUI workflow after generation', elem_id='sd-comfyui-webui-run-after-generate')
        return run_comfyui_after_generation,

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def postprocess(self, p, res, run_comfyui_after_generation):
        if not run_comfyui_after_generation:
            return

        batches = [[img] for img in res.images]

        for batch in batches:
            shared.last_output_images = batch
            shared.last_batch_length = len(batch)
            queue_prompt_button.send_request()


webui_callbacks.register_callbacks()
