import torch
from lib_comfyui import global_state


class WebuiLatentInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("LATENT", )
    FUNCTION = "fetch_images"

    CATEGORY = "webui"

    def fetch_images(self, void):
        tab_name = global_state.tab_name
        key = f'{tab_name}_node_inputs'
        return {'samples': getattr(global_state, key)},


NODE_CLASS_MAPPINGS = {
    "LatentFromWebui": WebuiLatentInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LatentFromWebui": 'Latent From Webui',
}
