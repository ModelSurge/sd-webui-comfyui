import torch
from lib_comfyui import global_state


class WebuiImageInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "get_images"

    CATEGORY = "webui"

    def get_images(self, void):
        tab_name = global_state.tab_name
        key = f'{tab_name}_node_inputs'
        return torch.stack(getattr(global_state, key)).permute(0, 2, 3, 1),


NODE_CLASS_MAPPINGS = {
    "ImageFromWebui": WebuiImageInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageFromWebui": 'Image From Webui',
}
