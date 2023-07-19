from torchvision.transforms.functional import to_pil_image


expected_node_types = ['WebuiPostprocessInput', 'WebuiPostprocessOutput']


class WebuiPostprocessOutput:
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
        import webui_process
        webui_process.postprocessed_images = [to_pil_image(img) for img in images.permute(0, 3, 1, 2)]
        return []


NODE_CLASS_MAPPINGS = {
    "WebuiPostprocessOutput": WebuiPostprocessOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiPostprocessOutput": 'Webui Postprocess Output',
}
