from modules import shared

from comfy.sd import load_checkpoint_guess_config
from comfy import utils


class CheckpointLoaderPatched(object):
    def __enter__(self):
        self.original_loader = utils.load_torch_file
        utils.load_torch_file = self.load_torch_file
        return self

    def __exit__(self, type, value, traceback):
        utils.load_torch_file = self.original_loader

    def load_torch_file(self, sd, safe_load=False):
        patched_sd = {}
        expected_keys = ('cond_stage_model', 'first_stage_model', 'model.diffusion_model')
        for k, v in sd.items():
            if not k.startswith(expected_keys):
                continue
            k = k.replace('.wrapped', '')
            patched_sd[k] = v
        return patched_sd


class WebuiCheckpointLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                    "integer": ("INT", {"default": 0, "min": -0xffffffffffffffff, "max": 0xffffffffffffffff}),
            },
        }
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load_checkpoint"

    CATEGORY = "loaders"

    def load_checkpoint(self, integer):
        with CheckpointLoaderPatched():
            return load_checkpoint_guess_config(shared.sd_model_state_dict)


NODE_CLASS_MAPPINGS = {
    "WebuiCheckpointLoader": WebuiCheckpointLoader,
}
