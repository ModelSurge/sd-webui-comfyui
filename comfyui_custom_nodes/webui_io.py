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
        return torch.stack(global_state.node_inputs).permute(0, 2, 3, 1),


class WebuiImageOutput:
    images = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", ),
            },
        }
    RETURN_TYPES = ()
    FUNCTION = "set_images"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    def set_images(self, images):
        global_state.node_outputs += images.permute(0, 3, 1, 2)
        return []


class WebuiLatentInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("LATENT", )
    FUNCTION = "get_latents"

    CATEGORY = "webui"

    def get_latents(self, void):
        return {'samples': global_state.node_inputs},


class WebuiLatentOutput:
    images = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latents": ("LATENT", ),
            },
        }
    RETURN_TYPES = ()
    FUNCTION = "set_images"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    def set_images(self, latents):
        global_state.node_outputs += latents['samples'].to('cpu')
        return []


NODE_CLASS_MAPPINGS = {
    "ImageFromWebui": WebuiImageInput,
    "ImageToWebui": WebuiImageOutput,
    "LatentFromWebui": WebuiLatentInput,
    "LatentToWebui": WebuiLatentOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageFromWebui": 'Image From Webui',
    "ImageToWebui": 'Image To Webui',
    "LatentFromWebui": 'Latent From Webui',
    "LatentToWebui": 'Latent To Webui',
}
