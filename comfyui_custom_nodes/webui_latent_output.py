from lib_comfyui import global_state


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
    FUNCTION = "fetch_images"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    def fetch_images(self, latents):
        tab_name = global_state.tab_name
        key = f'{tab_name}_node_outputs'
        generated_images = getattr(global_state, key, [])
        generated_images.extend(latents['samples'].to('cpu'))
        setattr(global_state, key, generated_images)
        return []


NODE_CLASS_MAPPINGS = {
    "LatentToWebui": WebuiLatentOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LatentToWebui": 'Latent To Webui',
}
