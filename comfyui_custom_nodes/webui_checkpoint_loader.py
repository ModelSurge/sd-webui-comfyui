import torch
import webui_process
import comfy


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
        return torch.half

    def model_patches_to(self, device):
        return

    def patch_model(self):
        return self.model

    def unpatch_model(self):
        return

    @property
    def model_options(self):
        return {"transformer_options": {}}


class WebuiModel:
    @property
    def latent_format(self):
        return comfy.latent_formats.SD15()

    def process_latent_in(self, latent):
        return self.latent_format.process_in(latent)

    def process_latent_out(self, latent):
        return self.latent_format.process_out(latent)

    def to(self, device):
        assert str(device) == str(self.device), f"cannot move the webui checkpoint to a different device. tried to move from {self.device} to {device}"
        return self

    def is_adm(self):
        return False

    def apply_model(self, *args, **kwargs):
        args = list(args)
        del kwargs['transformer_options']

        for k, v in enumerate(args):
            if isinstance(v, torch.Tensor):
                args[k] = v.cpu()

        for k, v in kwargs.items():
            if isinstance(v, torch.Tensor):
                kwargs[k] = v.cpu()
            elif isinstance(v, list):
                for i, vv in enumerate(v):
                    if isinstance(vv, torch.Tensor):
                        v[i] = vv.cpu()

        return webui_process.apply_model(*args, **kwargs).to(self.device)

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        if item == 'concat_keys':
            raise AttributeError

        res = webui_process.fetch_model_attribute(item)
        if isinstance(res, torch.Tensor):
            return res.to(device=self.device)

        return res
