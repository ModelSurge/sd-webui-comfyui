from lib_comfyui.webui_proxies import WebuiModelPatcher, WebuiModelProxy, WebuiVaeWrapper, WebuiVaeProxy


class WebuiCheckpointLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                    "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("MODEL", "VAE",)
    FUNCTION = "load_checkpoint"

    CATEGORY = "loaders"

    def load_checkpoint(self, void):
        return (
            WebuiModelPatcher(WebuiModelProxy()),
            WebuiVaeWrapper(WebuiVaeProxy()),
        )


NODE_CLASS_MAPPINGS = {
    "WebuiCheckpointLoader": WebuiCheckpointLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiCheckpointLoader": 'Webui Checkpoint',
}
