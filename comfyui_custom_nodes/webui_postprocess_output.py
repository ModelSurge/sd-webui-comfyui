from lib_comfyui import global_state


expected_node_types = []


class WebuiPostprocessOutput:
    images = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", ),
            },
        }
    RETURN_TYPES = ()
    FUNCTION = "fetch_images"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    def fetch_images(self, images):
        tab_name = global_state.tab_name
        key = f'{tab_name}_postprocess_output_images'
        generated_images = getattr(global_state, key, [])
        generated_images.extend(images.permute(0, 3, 1, 2).cpu())
        setattr(global_state, key, generated_images)
        return []


NODE_CLASS_MAPPINGS = {
    "PostprocessToWebui": WebuiPostprocessOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PostprocessToWebui": 'Postprocess To Webui',
}
