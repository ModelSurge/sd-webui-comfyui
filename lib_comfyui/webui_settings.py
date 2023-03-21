from modules import shared
import importlib
import install_comfyui
importlib.reload(install_comfyui)


def create_section():
    section = ('comfyui', "ComfyUI")
    shared.opts.add_option("comfyui_install_location", shared.OptionInfo(
        install_comfyui.default_install_location, "ComfyUI install location", section=section))
    shared.opts.add_option("comfyui_additional_args", shared.OptionInfo(
        '', "Additional cli arguments to pass to ComfyUI (requires reload UI)", section=section))


def get_install_location():
    install_location = install_comfyui.default_install_location
    install_location = shared.opts.data.get('comfyui_install_location', install_location).strip()
    return install_location


def get_additional_argv():
    return [arg.strip() for arg in shared.opts.data.get('comfyui_additional_args', '').split()]


def get_url():
    global html_object_url
    return html_object_url if html_object_url else f'http://127.0.0.1:{get_port()}'


def get_port():
    webui_argv = get_additional_argv()
    port_index = webui_argv.index('--port') if '--port' in webui_argv else -1
    settings_port = webui_argv[port_index + 1] if port_index in range(len(webui_argv)) else None
    return settings_port or shared.cmd_opts.comfyui_port


html_object_url = ''


def set_comfyui_url(url):
    global html_object_url
    html_object_url = url
