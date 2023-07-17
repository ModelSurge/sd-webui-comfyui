import torch
import webui_process
from torchvision.transforms.functional import pil_to_tensor


class WebuiOutputImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                    "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "fetch_image"

    CATEGORY = "image"

    def fetch_image(self, void):
        return torch.stack([pil_to_tensor(img).permute(1, 2, 0)/255 for img in webui_process.fetch_last_output_images()]),


NODE_CLASS_MAPPINGS = {
    "WebuiOutputImage": WebuiOutputImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiOutputImage": 'Webui Output Image',
}
