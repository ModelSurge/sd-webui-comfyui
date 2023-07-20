import functools
import gc
import sys
import yaml
import textwrap
import torch
from lib_comfyui import webui_settings, ipc, torch_utils
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

    def clone(self):
        return self

    def set_model_patch(self, *args, **kwargs):
        soft_raise('patching a webui resource is not yet supported')

    def set_model_patch_replace(self, *args, **kwargs):
        soft_raise('patching a webui resource is not yet supported')

    def model_patches_to(self, device):
        return

    def model_dtype(self):
        return self.model.dtype

    def add_patches(self, *args, **kwargs):
        soft_raise('patching a webui resource is not yet supported')
        return []

    def get_key_patches(self, *args, **kwargs):
        return {}

    def model_state_dict(self, *args, **kwargs):
        soft_raise('accessing the webui checkpoint state dict from comfyui is not yet suppported')
        return {}

    def patch_model(self):
        return self.model

    def unpatch_model(self):
        return

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        import comfy
        return functools.partial(getattr(comfy.sd.ModelPatcher, item), self)


class WebuiModelProxy:
    @property
    def latent_format(self):
        return get_comfy_model_config().latent_format

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
        adm_in_channels = get_comfy_model_config().unet_config.get('adm_in_channels', None) or 0
        return adm_in_channels > 0

    def encode_adm(self, *args, **kwargs):
        raise NotImplementedError('webui v-prediction checkpoints are not yet supported')

    def apply_model(self, *args, **kwargs):
        args = torch_utils.deep_to(args, device='cpu')
        del kwargs['transformer_options']
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(WebuiModelProxy.sd_model_apply(*args, **kwargs), device=self.device)

    @ipc.confine_to('webui')
    @staticmethod
    def sd_model_apply(*args, **kwargs):
        args = torch_utils.deep_to(args, shared.sd_model.device)
        kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
        with devices.autocast(), torch.no_grad():
            res = shared.sd_model.model(*args, **kwargs).cpu().share_memory_()
            free_webui_memory()
            return res

    def state_dict(self):
        soft_raise('accessing the webui checkpoint state dict from comfyui is not yet suppported')
        return {}

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        res = WebuiModelProxy.sd_model_getattr(item)
        if item != "device":
            res = torch_utils.deep_to(res, device=self.device)

        return res

    @ipc.confine_to('webui')
    @staticmethod
    def sd_model_getattr(item):
        res = getattr(shared.sd_model, item)
        res = torch_utils.deep_to(res, 'cpu')
        return res


class WebuiClipWrapper:
    def __init__(self, proxy):
        self.cond_stage_model = proxy
        self.patcher = WebuiModelPatcher(self.cond_stage_model)

    @property
    def layer_idx(self):
        clip_skip = webui_settings.opts.CLIP_stop_at_last_layers
        return -clip_skip if clip_skip > 1 else None

    def clone(self):
        return self

    def load_from_state_dict(self, *args, **kwargs):
        return

    def clip_layer(self, layer_idx):
        soft_raise(f'cannot control webui clip skip from comfyui. Tried to stop at layer {layer_idx}')
        return

    def tokenize(self, *args, **kwargs):
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(WebuiClipWrapper.sd_clip_tokenize_with_weights(*args, **kwargs), device=self.cond_stage_model.device)

    @ipc.confine_to('webui')
    @staticmethod
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

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        import comfy
        return functools.partial(getattr(comfy.sd.CLIP, item), self)


class WebuiClipProxy:
    def clip_layer(self, layer_idx):
        soft_raise(f'cannot control webui clip skip from comfyui. Tried to stop at layer {layer_idx}')
        return

    def reset_clip_layer(self):
        return

    def encode_token_weights(self, *args, **kwargs):
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(WebuiClipProxy.sd_clip_encode_token_weights(*args, **kwargs), device=self.device)

    @ipc.confine_to('webui')
    @staticmethod
    def sd_clip_encode_token_weights(token_weight_pairs_list):
        tokens = [
            [pair[0] for pair in token_weight_pairs]
            for token_weight_pairs in token_weight_pairs_list
        ]
        weights = [
            [pair[1] for pair in token_weight_pairs]
            for token_weight_pairs in token_weight_pairs_list
        ]
        conds = [
            shared.sd_model.cond_stage_model.process_tokens([tokens], [weights])
            for tokens, weights in zip(tokens, weights)
        ]
        return torch.hstack(conds).cpu().share_memory_(), None

    def to(self, device):
        assert str(device) == str(self.device), textwrap.dedent(f'''
            cannot move the webui unet to a different device
            comfyui attempted to move it from {self.device} to {device}
        ''')
        return self

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        res = WebuiClipProxy.sd_clip_getattr(item)
        if item != "device":
            res = torch_utils.deep_to(res, device=self.device)

        return res

    @ipc.confine_to('webui')
    @staticmethod
    def sd_clip_getattr(item):
        res = getattr(shared.sd_model.cond_stage_model.wrapped.transformer, item)
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
        return self.first_stage_model.device

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        import comfy
        return functools.partial(getattr(comfy.sd.VAE, item), self)


class WebuiVaeProxy:
    def state_dict(self):
        soft_raise('accessing the webui checkpoint state dict from comfyui is not yet suppported')
        return {}

    def encode(self, *args, **kwargs):
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(WebuiVaeProxy.sd_vae_encode(*args, **kwargs), device=self.device)

    @ipc.confine_to('webui')
    @staticmethod
    def sd_vae_encode(*args, **kwargs):
        args = torch_utils.deep_to(args, shared.sd_model.device)
        kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
        with devices.autocast(), torch.no_grad():
            res = shared.sd_model.first_stage_model.encode(*args, **kwargs).cpu().share_memory_()
            free_webui_memory()
            return res

    def decode(self, *args, **kwargs):
        args = torch_utils.deep_to(args, device='cpu')
        kwargs = torch_utils.deep_to(kwargs, device='cpu')
        return torch_utils.deep_to(WebuiVaeProxy.sd_vae_decode(*args, **kwargs), device=self.device)

    @ipc.confine_to('webui')
    @staticmethod
    def sd_vae_decode(*args, **kwargs):
        args = torch_utils.deep_to(args, shared.sd_model.device)
        kwargs = torch_utils.deep_to(kwargs, shared.sd_model.device)
        with devices.autocast(), torch.no_grad():
            res = shared.sd_model.first_stage_model.decode(*args, **kwargs).cpu().share_memory_()
            free_webui_memory()
            return res

    def to(self, device):
        assert str(device) == str(self.device), textwrap.dedent(f'''
            cannot move the webui unet to a different device
            comfyui attempted to move it from {self.device} to {device}
        ''')
        return self

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        res = WebuiVaeProxy.sd_vae_getattr(item)
        if item != "device":
            res = torch_utils.deep_to(res, device=self.device)

        return res

    @ipc.confine_to('webui')
    @staticmethod
    def sd_vae_getattr(item):
        res = getattr(shared.sd_model.first_stage_model, item)
        res = torch_utils.deep_to(res, 'cpu')
        return res


@ipc.confine_to('webui')
def free_webui_memory():
    gc.collect(1)
    torch.cuda.empty_cache()


@ipc.confine_to('comfyui')
def raise_on_unsupported_model_type(config):
    import comfy
    if type(config) not in (
        comfy.supported_models.SD15,
        comfy.supported_models.SD20,
    ):
        raise NotImplementedError(f'Webui model type {type(config).__name__} is not yet supported')


@ipc.confine_to('comfyui')
def get_comfy_model_config():
    import comfy
    with open(sd_model_get_config()) as f:
        config_dict = yaml.safe_load(f)

    unet_config = config_dict['model']['params']['unet_config']['params']
    unet_config['use_linear_in_transformer'] = unet_config.get('use_linear_in_transformer', False)
    unet_config['adm_in_channels'] = unet_config.get('adm_in_channels', None)
    return comfy.model_detection.model_config_from_unet_config(unet_config)


@ipc.confine_to('webui')
def sd_model_get_config():
    return sd_models_config.find_checkpoint_config(shared.sd_model.state_dict(), sd_models.select_checkpoint())


def soft_raise(message):
    print(f'[sd-webui-comfyui] {message}', file=sys.stderr)
