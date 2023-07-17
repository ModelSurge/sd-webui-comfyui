import yaml
import textwrap

import torch
import comfy
import webui_process
from lib_comfyui import torch_utils


class WebuiCheckpointLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                    "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load_checkpoint"

    CATEGORY = "loaders"

    def load_checkpoint(self, void):
        return WebuiModelPatcher(WebuiModel()),


NODE_CLASS_MAPPINGS = {
    "WebuiCheckpointLoader": WebuiCheckpointLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiCheckpointLoader": 'Load Webui Checkpoint',
}


class WebuiModelPatcher:
    def __init__(self, model):
        self.model = model
        self.load_device = model.device
        self.offload_device = model.device

    def model_size(self):
        return 0

    def model_dtype(self):
        return self.model.dtype

    def model_patches_to(self, device):
        return

    def patch_model(self):
        return self.model

    def unpatch_model(self):
        return

    @property
    def model_options(self):
        return {'transformer_options': {}}


class WebuiModel:
    def get_comfy_config(self):
        with open(self.config_path) as f:
            config_dict = yaml.safe_load(f)

        unet_config = config_dict['model']['params']['unet_config']['params']
        unet_config['use_linear_in_transformer'] = unet_config.get('use_linear_in_transformer', False)
        unet_config['adm_in_channels'] = unet_config.get('adm_in_channels', None)
        return comfy.model_detection.model_config_from_unet_config(unet_config)

    @property
    def latent_format(self):
        return self.get_comfy_config().latent_format

    def process_latent_in(self, latent):
        return self.latent_format.process_in(latent)

    def process_latent_out(self, latent):
        return self.latent_format.process_out(latent)

    def to(self, device):
        assert str(device) == str(self.device), textwrap.dedent(f'''
            cannot move the webui unet to a different device
            comfyui attempted to move it from {self.device} to {device}
        ''')
        return self

    def is_adm(self):
        return self.get_comfy_config().unet_config.get('adm_in_channels', None) is not None

    def encode_adm(self, *args, **kwargs):
        raise NotImplementedError

    def apply_model(self, *args, **kwargs):
        args = torch_utils.deep_to(args, device='cpu', dtype=torch.half)
        del kwargs['transformer_options']
        kwargs = torch_utils.deep_to(kwargs, device='cpu', dtype=torch.half)
        return webui_process.apply_model(*args, **kwargs).to(device=self.device)

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        res = webui_process.fetch_model_attribute(item)
        if isinstance(res, torch.Tensor):
            return res.to(device=self.device)

        return res
