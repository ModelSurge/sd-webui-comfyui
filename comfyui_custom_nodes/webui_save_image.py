import os
from lib_comfyui.webui.settings import opts
from torchvision.transforms.functional import to_pil_image


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
        from modules.paths import data_path
        if 'txt2img' in location:
            output_dir = opts.outdir_samples or opts.outdir_txt2img_samples if 'images' in location else opts.outdir_grids or opts.outdir_txt2img_grids
        elif 'img2img' in location:
            output_dir = opts.outdir_samples or opts.outdir_img2img_samples if 'images' in location else opts.outdir_grids or opts.outdir_img2img_grids
        else:
            output_dir = opts.outdir_samples or opts.outdir_extras_samples

        for image in images:
            pil_image = to_pil_image(image.permute(2, 0, 1))
            save_path = os.path.join(data_path, output_dir)
            WebuiSaveImage.webui_save_image(image=pil_image, path=save_path, basename='')

        return []

    @staticmethod
    def webui_save_image(image, path, basename, *args, **kwargs):
        from lib_comfyui.webui.paths import webui_save_image
        return webui_save_image(image=image, path=path, basename=basename, *args, **kwargs)


NODE_CLASS_MAPPINGS = {
    "WebuiSaveImage": WebuiSaveImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiSaveImage": 'Webui Save Image',
}
