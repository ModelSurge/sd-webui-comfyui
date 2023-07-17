import gradio as gr
import modules.scripts as scripts
from modules import shared
import sys
from lib_comfyui import webui_callbacks, queue_prompt_button

base_dir = scripts.basedir()
sys.path.append(base_dir)


def split_list_every(list, n):
    limit = len(list) // n
    result = []

    for i in range(limit):
        lower = i * n
        upper = (i+1) * n
        result.append(list[lower:upper])
    last = limit * n
    if last < len(list):
        result.append(list[last:])

    return result


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

        images = res.images[res.index_of_first_image:]
        batches = split_list_every(images, res.batch_size)

        for batch in batches:
            shared.last_output_images = batch
            shared.last_batch_count = len(images) // res.batch_size
            queue_prompt_button.send_request()


webui_callbacks.register_callbacks()
