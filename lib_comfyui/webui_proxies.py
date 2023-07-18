import functools

import yaml
import textwrap
import torch
from lib_comfyui import torch_utils
from modules import shared, devices, sd_models, sd_models_config, prompt_parser


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
        return torch_utils.deep_to(webui_process.apply_model(*args, **kwargs), device=self.device)

    def __getattr__(self, item):
        import webui_process
        if item in self.__dict__:
            return self.__dict__[item]

        res = webui_process.fetch_model_attribute(item)
        if isinstance(res, torch.Tensor):
            return torch_utils.deep_to(res, device=self.device)

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
        return torch_utils.deep_to(webui_process.vae_encode(*args, **kwargs), device=self.device)

    def decode(self, *args, **kwargs):
        import webui_process
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(webui_process.vae_decode(*args, **kwargs), device=self.device)

    def __getattr__(self, item):
        import webui_process
        if item in self.__dict__:
            return self.__dict__[item]

        res = webui_process.fetch_vae_attribute(item)
        if isinstance(res, torch.Tensor):
            return torch_utils.deep_to(res, device=self.device)

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


class WebuiClipWrapper:
    def __init__(self, proxy):
        self.cond_stage_model = proxy
        self.patcher = WebuiModelPatcher(self.cond_stage_model)

    def tokenize(self, *args, **kwargs):
        import webui_process
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(webui_process.clip_tokenize_with_weights(*args, **kwargs), device=self.cond_stage_model.device)

    @property
    def layer_idx(self):
        import webui_process
        clip_skip = self.cond_stage_model.config.num_hidden_layers - webui_process.fetch_shared_opts().CLIP_stop_at_last_layers
        return clip_skip if clip_skip > 1 else None

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        import comfy
        return functools.partial(getattr(comfy.sd.CLIP, item), self)


class WebuiClipProxy:
    def clip_layer(self, idx):
        return

    def reset_clip_layer(self):
        return

    def encode_token_weights(self, *args, **kwargs):
        import webui_process
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(webui_process.clip_encode_token_weights(*args, **kwargs), device=self.device)

    def to(self, device):
        assert str(device) == str(self.device), textwrap.dedent(f'''
            cannot move the webui unet to a different device
            comfyui attempted to move it from {self.device} to {device}
        ''')
        return self

    def __getattr__(self, item):
        import webui_process
        if item in self.__dict__:
            return self.__dict__[item]

        res = webui_process.fetch_clip_attribute(item)
        if isinstance(res, torch.Tensor):
            return torch_utils.deep_to(res, device=self.device)

        return res


def sd_clip_getattr(item):
    res = getattr(shared.sd_model.cond_stage_model.wrapped.transformer, item)
    res = torch_utils.deep_to(res, 'cpu')
    return res


def sd_clip_tokenize_with_weights(text, return_word_ids=False):
    chunks, tokens_count, *_ = shared.sd_model.cond_stage_model.tokenize_line(text)
    weighted_tokens = [list(zip(chunk.tokens, chunk.multipliers)) for chunk in chunks]
    clip_max_len = shared.sd_model.cond_stage_model.wrapped.max_length
    if return_word_ids:
        padding_tokens_count = ((tokens_count // clip_max_len) + 1) * clip_max_len
        for token_i in range(padding_tokens_count):
            actual_id = token_i if token_i < tokens_count else 0
            weighted_tokens[token_i // clip_max_len][token_i % clip_max_len] += (actual_id,)

    return weighted_tokens


def sd_clip_encode_token_weights(token_weight_pairs_list):
    tokens = [[pair[0] for pair in token_weight_pairs] for token_weight_pairs in token_weight_pairs_list]
    weights = [[pair[1] for pair in token_weight_pairs] for token_weight_pairs in token_weight_pairs_list]
    conds = [shared.sd_model.cond_stage_model.process_tokens([tokens], [weights]) for tokens, weights in zip(tokens, weights)]
    return torch.hstack(conds), None
