import sys
import textwrap
import types
import json
from lib_comfyui import parallel_utils
from modules import shared
import install_comfyui


def create_section():
    section = ('comfyui', "ComfyUI")
    shared.opts.add_option("comfyui_install_location", shared.OptionInfo(
        install_comfyui.default_install_location, "ComfyUI install location", section=section))
    shared.opts.add_option("comfyui_additional_args", shared.OptionInfo(
        '', "Additional cli arguments to pass to ComfyUI (requires reload UI. Do NOT prepend --comfyui-, these are directly forwarded to comfyui)", section=section))
    shared.opts.add_option("comfyui_client_address", shared.OptionInfo(
        '', 'Address of the ComfyUI server as seen from the webui. Only used by the extension to load the ComfyUI iframe (requires reload UI)',
        component_args={'placeholder': 'Leave empty to use the --listen address of the ComfyUI server'}, section=section))


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
    return get_setting_value('--port') or getattr(shared.cmd_opts, 'comfyui_port', 8188)


def get_comfyui_client_url():
    loopback_address = '127.0.0.1'
    server_url = get_setting_value('--listen') or getattr(shared.cmd_opts, 'comfyui_listen', loopback_address)
    client_url = getattr(shared.opts.data, 'comfyui_client_address', None) or getattr(shared.cmd_opts, 'webui_comfyui_client_address', None) or server_url
    if client_url == '0.0.0.0':
        print(textwrap.dedent(f"""
            [ComfyUI extension] changing the ComfyUI client address from {client_url} to {loopback_address}
            This does not change the --listen address passed to ComfyUI, but instead the address used by the extension to load the iframe
            To override this behavior, navigate to the extension settings or use the --webui-comfyui-client-address <address> cli argument
        """), sys.stderr)
        client_url = loopback_address

    return f'http://{client_url}:{get_port()}/'


class WebuiOptions:
    def __getattr__(self, item):
        return WebuiOptions.opts_getattr(item)

    @parallel_utils.confine_to('webui')
    @staticmethod
    def opts_getattr(item):
        return getattr(shared.opts, item)


opts = WebuiOptions()
