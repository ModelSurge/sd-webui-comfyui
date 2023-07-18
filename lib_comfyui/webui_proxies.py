import functools

import yaml
import textwrap
import torch
from lib_comfyui import torch_utils
from modules import shared, devices, sd_models, sd_models_config


class WebuiModelPatcher:
    def __init__(self, model):
        self.model = model
        self.load_device = model.device
        self.offload_device = model.device
        self.model_options = {'transformer_options': {}}

    def model_size(self):
        # returning 0 means to manage the model with VRAMState.NORMAL_VRAM
        # https://github.com/comfyanonymous/ComfyUI/blob/ee8f8ee07fb141e5a5ce3abf602ed0fa2e50cf7b/comfy/model_management.py#L272-L276
        return 0

    def model_dtype(self):
        return self.model.dtype

    def model_patches_to(self, device):
        return

    def patch_model(self):
        return self.model

    def unpatch_model(self):
        return


class WebuiModelProxy:
    CONFIG_PATH_ATTRIBUTE = 'config_path'

    def get_comfy_model_config(self):
        import comfy
        with open(getattr(self, WebuiModelProxy.CONFIG_PATH_ATTRIBUTE)) as f:
            config_dict = yaml.safe_load(f)

        unet_config = config_dict['model']['params']['unet_config']['params']
        unet_config['use_linear_in_transformer'] = unet_config.get('use_linear_in_transformer', False)
        unet_config['adm_in_channels'] = unet_config.get('adm_in_channels', None)
        return comfy.model_detection.model_config_from_unet_config(unet_config)

    @property
    def latent_format(self):
        return self.get_comfy_model_config().latent_format

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
        adm_in_channels = self.get_comfy_model_config().unet_config.get('adm_in_channels', None) or 0
        return adm_in_channels > 0

    def encode_adm(self, *args, **kwargs):
        raise NotImplementedError

    def apply_model(self, *args, **kwargs):
        import webui_process
        args = torch_utils.deep_to(args, device='cpu')
        del kwargs['transformer_options']
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return webui_process.apply_model(*args, **kwargs).to(device=self.device)

    def __getattr__(self, item):
        import webui_process
        if item in self.__dict__:
            return self.__dict__[item]

        res = webui_process.fetch_model_attribute(item)
        if isinstance(res, torch.Tensor):
            return res.to(device=self.device)

        return res


def sd_model_apply(*args, **kwargs):
    args = torch_utils.deep_to(args, shared.sd_model.device)
    kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
    with devices.autocast(), torch.no_grad():
        res = shared.sd_model.model(*args, **kwargs)
        return res.cpu()


def sd_model_getattr(item):
    if item == WebuiModelProxy.CONFIG_PATH_ATTRIBUTE:
        return sd_models_config.find_checkpoint_config(shared.sd_model.state_dict(), sd_models.select_checkpoint())

    res = getattr(shared.sd_model, item)
    res = torch_utils.deep_to(res, 'cpu')
    return res


class WebuiVaeWrapper:
    def __init__(self, proxy):
        self.first_stage_model = proxy

    @property
    def vae_dtype(self):
        return self.first_stage_model.dtype

    @property
    def device(self):
        return self.first_stage_model.device

    @property
    def offload_device(self):
        return self.device

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        import comfy
        return functools.partial(getattr(comfy.sd.VAE, item), self)


class WebuiVaeProxy:
    def to(self, device):
        assert str(device) == str(self.device), textwrap.dedent(f'''
            cannot move the webui unet to a different device
            comfyui attempted to move it from {self.device} to {device}
        ''')
        return self

    def encode(self, *args, **kwargs):
        import webui_process
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return webui_process.vae_encode(*args, **kwargs).to(device=self.device)

    def decode(self, *args, **kwargs):
        import webui_process
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return webui_process.vae_decode(*args, **kwargs).to(device=self.device)

    def __getattr__(self, item):
        import webui_process
        if item in self.__dict__:
            return self.__dict__[item]

        res = webui_process.fetch_vae_attribute(item)
        if isinstance(res, torch.Tensor):
            return res.to(device=self.device)

        return res


def sd_vae_getattr(item):
    res = getattr(shared.sd_model.first_stage_model, item)
    res = torch_utils.deep_to(res, 'cpu')
    return res


def sd_vae_encode(*args, **kwargs):
    args = torch_utils.deep_to(args, shared.sd_model.device)
    kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
    with devices.autocast(), torch.no_grad():
        res = shared.sd_model.first_stage_model.encode(*args, **kwargs)
        return res.cpu()


def sd_vae_decode(*args, **kwargs):
    args = torch_utils.deep_to(args, shared.sd_model.device)
    kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
    with devices.autocast(), torch.no_grad():
        res = shared.sd_model.first_stage_model.decode(*args, **kwargs)
        return res.cpu()
