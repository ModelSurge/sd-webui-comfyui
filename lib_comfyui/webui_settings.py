from modules import shared
import importlib
import install_comfyui
importlib.reload(install_comfyui)


def create_section():
    section = ('comfyui', "ComfyUI")
    shared.opts.add_option("comfyui_install_location", shared.OptionInfo(
        install_comfyui.default_install_location, "ComfyUI install location", section=section))
    shared.opts.add_option("comfyui_additional_args", shared.OptionInfo(
        '', "Additional cli arguments to pass to ComfyUI (requires reload UI. Do NOT prepend `--comfyui-`, these are literally forwarded to comfyui)", section=section))


def get_install_location():
    install_location = install_comfyui.default_install_location
    install_location = shared.opts.data.get('comfyui_install_location', install_location).strip()
    return install_location


def get_additional_argv():
    return [arg.strip() for arg in shared.opts.data.get('comfyui_additional_args', '').split()]


def get_setting_value(setting_key):
    webui_argv = get_additional_argv()
    index = webui_argv.index(setting_key) if setting_key in webui_argv else -1
    setting_value = webui_argv[index + 1] if 0 <= index < len(webui_argv) - 1 else None
    return setting_value


def get_port():
    return get_setting_value('--port') or shared.cmd_opts.comfyui_port


def get_comfyui_client_url():
    return f'http://127.0.0.1:{get_port()}/'
