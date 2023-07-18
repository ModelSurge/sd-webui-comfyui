import webui_process
from modules import shared


class WebuiPostprocessOutput:
    node_id = 0

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", ),
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ()
    FUNCTION = "fetch_images"

    CATEGORY = "image"

    OUTPUT_NODE = True

    def fetch_images(self, images, void):
        shared.last_output_images = images.permute(0, 3, 1, 2)
        return []


NODE_CLASS_MAPPINGS = {
    "WebuiPostprocessOutput": WebuiPostprocessOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiPostprocessOutput": 'Webui Postprocess Output',
}
