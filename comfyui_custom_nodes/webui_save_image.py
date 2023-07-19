import os
from lib_comfyui import webui_settings
from torchvision.transforms.functional import to_pil_image
from modules.images import save_image
from modules.paths import data_path


class WebuiSaveImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                    "location": (["txt2img-images", "img2img-images", "extras-images", "txt2img-grids", "img2img-grids", ], ),
                    "images": ("IMAGE", ),
            },
        }
    RETURN_TYPES = ()
    FUNCTION = "save_image"

    CATEGORY = "image"

    OUTPUT_NODE = True

    def save_image(self, location, images):
        opts = webui_settings.fetch_shared_opts()
        if 'txt2img' in location:
            output_dir = opts.outdir_samples or opts.outdir_txt2img_samples if 'images' in location else opts.outdir_grids or opts.outdir_txt2img_grids
        elif 'img2img' in location:
            output_dir = opts.outdir_samples or opts.outdir_img2img_samples if 'images' in location else opts.outdir_grids or opts.outdir_img2img_grids
        else:
            output_dir = opts.outdir_samples or opts.outdir_extras_samples

        for image in images:
            pil_image = to_pil_image(image.permute(2, 0, 1))
            save_path = os.path.join(data_path, output_dir)
            filename, _ = save_image(image=pil_image, path=save_path, basename='')

        return []


NODE_CLASS_MAPPINGS = {
    "WebuiTxt2ImgOutput": WebuiSaveImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiTxt2ImgOutput": 'Webui Save Image',
}
