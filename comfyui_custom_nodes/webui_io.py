import torch
from lib_comfyui import global_state
from lib_comfyui.comfyui.webui_io import NODE_DISPLAY_NAME_MAPPINGS

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


def get_sd_model_multiplier():
    from lib_comfyui.webui.proxies import sd_model_get_config
    import yaml
    with open(sd_model_get_config(), 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
        return config['model']['params']['scale_factor']


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
        multiplier = get_sd_model_multiplier()
        return {'samples': global_state.node_inputs / multiplier},


class WebuiLatentOutput:
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
        multiplier = get_sd_model_multiplier()
        global_state.node_outputs += latents['samples'].to('cpu') * multiplier
        return []


NODE_CLASS_MAPPINGS = {
    "ImageFromWebui": WebuiImageInput,
    "ImageToWebui": WebuiImageOutput,
    "LatentFromWebui": WebuiLatentInput,
    "LatentToWebui": WebuiLatentOutput,
}
