import torch
from lib_comfyui import global_state


class WebuiPostprocessInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "fetch_images"

    CATEGORY = "webui"

    def fetch_images(self, void):
        tab_name = global_state.tab_name
        key = f'{tab_name}_postprocess_input_images'
        return torch.stack(getattr(global_state, key)).permute(0, 2, 3, 1),


NODE_CLASS_MAPPINGS = {
    "PostprocessFromWebui": WebuiPostprocessInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PostprocessFromWebui": 'Postprocess From Webui',
}
