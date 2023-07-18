import webui_process


class WebuiPostprocessInput:
    node_id = 0

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "fetch_images"

    CATEGORY = "image"

    def fetch_images(self, void):
        return webui_process.fetch_last_output_images().permute(0, 2, 3, 1),


NODE_CLASS_MAPPINGS = {
    "WebuiPostprocessInput": WebuiPostprocessInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiPostprocessInput": 'Webui Postprocess Input',
}
