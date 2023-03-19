import sys
from modules import shared


comfyui_argv_prefix = 'comfyui_'


def set_comfyui_argv():
    sys.argv = sys.argv[:1] + extract_comfyui_argv()


def extract_comfyui_argv():
    result = []
    for k, v in _items(shared.cmd_opts):
        if k.startswith(comfyui_argv_prefix):
            k = k.replace(comfyui_argv_prefix, '')
            result.extend(as_argv_list(k, v))
    return result


def as_argv_list(k, v):
    result = []
    if is_used_argv(k, v):
        result.append(f'--{k.replace("_", "-")}')
        if is_paired_argv(k, v):
            result.append(str(v))
    return result


def _items(cmd_opts):
    return vars(cmd_opts).items()


def is_used_argv(k, v):
    return v not in [False, None]


def is_paired_argv(k, v):
    return v is not True
