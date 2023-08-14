import torch
from PIL import Image
import torchvision.transforms.functional as F
from lib_comfyui import ipc
from lib_comfyui.webui.proxies import get_comfy_model_config


def webui_image_to_comfyui(batch):
    if isinstance(batch[0], Image.Image):
        batch = torch.stack([F.pil_to_tensor(image) / 255 for image in batch])
    return batch.permute(0, 2, 3, 1)


def comfyui_image_to_webui(batch, return_tensors=False):
    batch = batch.permute(0, 3, 1, 2)
    if return_tensors:
        return batch

    return [F.to_pil_image(image) for image in batch]


@ipc.run_in_process('comfyui')
def webui_latent_to_comfyui(batch):
    latent_format = get_comfy_model_config().latent_format
    return {'samples': latent_format.process_out(batch)}


@ipc.run_in_process('comfyui')
def comfyui_latent_to_webui(batch):
    latent_format = get_comfy_model_config().latent_format
    return latent_format.process_in(batch['samples'])
