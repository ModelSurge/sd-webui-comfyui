from torchvision.transforms.functional import to_pil_image
from lib_comfyui import global_state


expected_node_types = [{'type': 'WebuiPostprocessInput', 'count': 1}, {'type': 'WebuiPostprocessOutput', 'count': 1}]


class WebuiPostprocessOutput:
    images = None

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
        tab_name = global_state.tab_name
        key = f'{tab_name}_postprocess_output_images'
        setattr(global_state, key, [to_pil_image(img) for img in images.permute(0, 3, 1, 2)])
        return []


NODE_CLASS_MAPPINGS = {
    "WebuiPostprocessOutput": WebuiPostprocessOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiPostprocessOutput": 'Webui Postprocess Output',
}
