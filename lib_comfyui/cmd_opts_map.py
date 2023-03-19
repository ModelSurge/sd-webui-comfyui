import sys
from modules import shared


comfyui_argv_prefix = '--comfyui-'


def set_comfyui_command_args():
    sys.argv = sys.argv[:1]
    argv = convert_arguments(shared.cmd_opts)
    sys.argv.extend(argv)


def convert_arguments(cmd_opts):
    result = []
    for k, v in _items(cmd_opts):
        if k.startswith(comfyui_argv_prefix):
            k = k.replace(comfyui_argv_prefix[2:], '')
            result.extend(as_argv_list(k, v))
    return result


def as_argv_list(k, v):
    result = []
    if is_used_argv(k, v):
        result.append(k)
        if is_paired_argv(k, v):
            result.append(v)
    return result


def _items(cmd_opts):
    return vars(cmd_opts).items()


def is_used_argv(k, v):
    return type(v) is str or v


def is_paired_argv(k, v):
    return type(v) is str
