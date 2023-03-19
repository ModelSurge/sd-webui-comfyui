comfyui_keyword = 'comfyui-'


def _items(cmd_opts):
    return vars(cmd_opts).items()


def convert_arguments(cmd_opts):
    comfyui_cmd_opts = {}
    for k, v in _items(cmd_opts):
        if comfyui_keyword in k:
            comfyui_key = k.replace(comfyui_keyword, '')
            comfyui_cmd_opts[comfyui_key] = v
    return comfyui_cmd_opts
