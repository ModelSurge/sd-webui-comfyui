from lib_comfyui.webui import proxies
from lib_comfyui import global_state


class WebuiCheckpointLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                    "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load_checkpoint"

    CATEGORY = "loaders"

    def load_checkpoint(self, void):
        config = proxies.get_comfy_model_config()
        proxies.raise_on_unsupported_model_type(config)
        return (
            proxies.ModelPatcher(proxies.Model()),
            proxies.ClipWrapper(proxies.Clip()),
            proxies.VaeWrapper(proxies.Vae()),
        )


class WebuiPrompts:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                    "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "get_prompts"

    CATEGORY = "loaders"

    def get_prompts(self, void):
        positive_prompts, _extra_networks = proxies.extra_networks_parse_prompts([getattr(global_state, 'last_positive_prompt', '')])

        return (
            positive_prompts[0],
            getattr(global_state, 'last_negative_prompt', ''),
        )


NODE_CLASS_MAPPINGS = {
    "WebuiCheckpointLoader": WebuiCheckpointLoader,
    "WebuiPrompts": WebuiPrompts,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiCheckpointLoader": 'Webui Checkpoint',
    "WebuiPrompts": "Webui Prompts",
}
