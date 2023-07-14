import os
import sys
import importlib
from modules import sd_models, paths, shared, modelloader


def share_webui_folder_paths(folder_paths: dict):
    from folder_paths import add_model_folder_path
    for folder_id, folder_paths in folder_paths.items():
        for folder_path in folder_paths:
            add_model_folder_path(folder_id, folder_path)


def get_folder_paths() -> dict:
    return {
        'checkpoints': [sd_models.model_path] + ([shared.cmd_opts.ckpt_dir] if shared.cmd_opts.ckpt_dir else []),
        'vae': [os.path.join(paths.models_path, 'VAE')] + ([shared.cmd_opts.vae_dir] if shared.cmd_opts.vae_dir else []),
        'embeddings': [shared.cmd_opts.embeddings_dir],
        'loras': [shared.cmd_opts.lora_dir],
        'hypernetworks': [shared.cmd_opts.hypernetwork_dir],
        'upscale_models': get_upscaler_paths(),
        'controlnet': get_controlnet_paths()
    }


# see https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/f865d3e11647dfd6c7b2cdf90dde24680e58acd8/modules/modelloader.py#L137
def get_upscaler_paths():
    # We can only do this 'magic' method to dynamically load upscalers if they are referenced,
    # so we'll try to import any _model.py files before looking in __subclasses__
    modules_dir = os.path.join(shared.script_path, "modules")
    for file in os.listdir(modules_dir):
        if "_model.py" in file:
            model_name = file.replace("_model.py", "")
            full_model = f"modules.{model_name}_model"
            try:
                importlib.import_module(full_model)
            except Exception:
                pass

    # some of upscaler classes will not go away after reloading their modules, and we'll end
    # up with two copies of those classes. The newest copy will always be the last in the list,
    # so we go from end to beginning and ignore duplicates
    used_classes = {}
    for cls in reversed(modelloader.Upscaler.__subclasses__()):
        class_name = str(cls)
        if class_name not in used_classes:
            used_classes[class_name] = cls

    upscaler_paths = set()
    for cls in reversed(used_classes.values()):
        name = cls.__name__
        cmd_name = f"{name.lower().replace('upscaler', '')}_models_path"
        commandline_model_path = getattr(shared.cmd_opts, cmd_name, None)
        scaler = cls(commandline_model_path)
        scaler_path = commandline_model_path or scaler.model_path
        if scaler_path is not None and not scaler_path.endswith("None"):
            upscaler_paths.add(scaler_path)

    return upscaler_paths


# see https://github.com/Mikubill/sd-webui-controlnet/blob/07bed6ccf8a468a45b2833cfdadc749927cbd575/scripts/global_state.py#L205
def get_controlnet_paths():
    controlnet_path = os.path.join(shared.extensions_dir, 'sd-webui-controlnet')
    try:
        sys.path.insert(0, controlnet_path)
        controlnet = importlib.import_module('extensions.sd-webui-controlnet.scripts.external_code', 'external_code')
    except:
        return []
    finally:
        sys.path.pop(sys.path.index(controlnet_path))

    ext_dirs = (shared.opts.data.get("control_net_models_path", None), getattr(shared.cmd_opts, 'controlnet_dir', None))
    extra_lora_paths = (extra_lora_path for extra_lora_path in ext_dirs
                        if extra_lora_path is not None and os.path.exists(extra_lora_path))
    return [
        controlnet.global_state.cn_models_dir,
        controlnet.global_state.cn_models_dir_old,
        *extra_lora_paths
    ]
