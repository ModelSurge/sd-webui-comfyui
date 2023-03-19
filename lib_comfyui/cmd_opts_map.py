comfyui_keyword = 'comfyui-'


def _items(cmd_opts):
    return vars(cmd_opts).items()


def is_double_argv(k, v):
    return not (type(v) is 'bool' and v)


def as_argv_list(k, v):
    result = []
    comfyui_key = k.replace(comfyui_keyword, '')
    result.append(comfyui_key)
    if is_double_argv(comfyui_key, v):
        result.append(v)
    return result


def convert_arguments(cmd_opts):
    result = []
    for k, v in _items(cmd_opts):
        if comfyui_keyword in k:
            result.extend(as_argv_list(k, v))
    return result
