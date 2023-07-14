from modules import shared

from comfy.sd import load_checkpoint_guess_config
from comfy import utils


class CheckpointLoaderPatched(object):
    def __init__(self, state_dict):
        self.state_dict = state_dict

    def __enter__(self):
        self.original_loader = utils.load_torch_file
        utils.load_torch_file = CheckpointLoaderPatched._load_torch_file
        return self

    def __exit__(self, type, value, traceback):
        utils.load_torch_file = self.original_loader

    @staticmethod
    def _load_torch_file(sd, safe_load=False):
        patched_sd = {}
        expected_keys = ('cond_stage_model', 'first_stage_model', 'model.diffusion_model')
        for k, v in sd.items():
            if not k.startswith(expected_keys):
                continue
            k = k.replace('.wrapped', '')
            patched_sd[k] = v
        return patched_sd

    def load(self):
        return load_checkpoint_guess_config(self.state_dict)


class WebuiCheckpointLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                    "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load_checkpoint"

    CATEGORY = "loaders"

    def load_checkpoint(self, void):
        with CheckpointLoaderPatched(shared.sd_model_state_dict) as patched_loader:
            return patched_loader.load()


NODE_CLASS_MAPPINGS = {
    "WebuiCheckpointLoader": WebuiCheckpointLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WebuiCheckpointLoader": 'Load Webui Checkpoint',
}
