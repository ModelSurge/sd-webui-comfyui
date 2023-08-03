from lib_comfyui.webui import proxies


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


NODE_CLASS_MAPPINGS = {
    "WebuiCheckpointLoader": WebuiCheckpointLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiCheckpointLoader": 'Webui Checkpoint',
}
