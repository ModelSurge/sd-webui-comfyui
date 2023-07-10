import sys
from modules import shared
from lib_comfyui import webui_settings


COMFYUI_ARGV_PREFIX = 'comfyui_'


def set_comfyui_argv():
    sys.argv = sys.argv[:1] + webui_settings.get_additional_argv() + extract_comfyui_argv()
    deduplicate_comfyui_args(sys.argv)


def extract_comfyui_argv():
    result = []
    for k, v in _items(shared.cmd_opts):
        if k.startswith(COMFYUI_ARGV_PREFIX):
            k = k.replace(COMFYUI_ARGV_PREFIX, '')
            result.extend(as_argv_list(k, v))
    return result


def as_argv_list(k, v):
    result = []
    if is_used_argv(k, v):
        result.append(f'--{k.replace("_", "-")}')
        if is_paired_argv(k, v):
            result.append(str(v))
    return result


def deduplicate_comfyui_args(argv):
    seen_args = set()
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in seen_args:
            if arg in ('--port',):
                len_to_remove = 2
            elif arg in ('--listen',):
                has_value = i + 1 < len(argv) and not argv[i + 1].startswith('--')
                len_to_remove = 1 + int(has_value)
            else:
                len_to_remove = 1
            argv[i:i + len_to_remove] = ()
        else:
            if arg.startswith('--'):
                seen_args.add(arg)
            i += 1


def _items(cmd_opts):
    return vars(cmd_opts).items()


def is_used_argv(k, v):
    return v not in [False, None]


def is_paired_argv(k, v):
    return v is not True
