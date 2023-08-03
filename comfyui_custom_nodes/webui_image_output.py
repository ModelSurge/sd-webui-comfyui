from lib_comfyui import global_state


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
        tab_name = global_state.tab_name
        key = f'{tab_name}_node_outputs'
        generated_images = getattr(global_state, key, [])
        generated_images.extend(images.permute(0, 3, 1, 2))
        setattr(global_state, key, generated_images)
        return []


NODE_CLASS_MAPPINGS = {
    "ImageToWebui": WebuiImageOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageToWebui": 'Image To Webui',
}
