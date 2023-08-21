import sys
import textwrap
from pathlib import Path
from lib_comfyui import ipc, global_state
import install_comfyui


@ipc.restrict_to_process('webui')
def create_section():
    from modules import shared
    import gradio as gr

    section = ('comfyui', "ComfyUI")
    shared.opts.add_option('comfyui_enabled', shared.OptionInfo(True, 'Enable sd-webui-comfyui extension', section=section))

    shared.opts.add_option("comfyui_update_button", shared.OptionInfo(
        "Update comfyui (requires reload ui)", "Update comfyui", gr.Button, section=section))

    shared.opts.add_option("comfyui_install_location", shared.OptionInfo(
        install_comfyui.default_install_location, "ComfyUI install location", section=section))
    shared.opts.add_option("comfyui_additional_args", shared.OptionInfo(
        '', "Additional cli arguments to pass to ComfyUI (requires reload UI. Do NOT prepend --comfyui-, these are directly forwarded to comfyui)", section=section))
    shared.opts.add_option("comfyui_client_address", shared.OptionInfo(
        '', 'Address of the ComfyUI server as seen from the webui. Only used by the extension to load the ComfyUI iframe (requires reload UI)',
        component_args={'placeholder': 'Leave empty to use the --listen address of the ComfyUI server'}, section=section))

    shared.opts.onchange('comfyui_enabled', update_enabled)

    shared.opts.add_option("comfyui_ipc_strategy", shared.OptionInfo(
        next(iter(ipc_strategy_choices.keys())), "Interprocess communication strategy", gr.Dropdown, lambda: {"choices": list(ipc_strategy_choices.keys())}, section=section))
    shared.opts.onchange('comfyui_ipc_strategy', update_ipc_strategy)
    update_ipc_strategy()

    shared.opts.add_option("comfyui_graceful_termination_timeout", shared.OptionInfo(
        5, 'ComfyUI server graceful termination timeout (in seconds) when reloading the gradio UI (-1 to block until the ComfyUI server exits normally)', gr.Number, section=section))
    shared.opts.onchange('comfyui_graceful_termination_timeout', update_comfyui_graceful_termination_timeout)
    update_comfyui_graceful_termination_timeout()

    shared.opts.add_option("comfyui_reverse_proxy_enabled", shared.OptionInfo(
        next(iter(reverse_proxy_choices.keys())), "Load ComfyUI iframes through a reverse proxy (requires reload UI. Needs --api. Default is on if webui is remote)", gr.Dropdown, lambda: {"choices": list(reverse_proxy_choices.keys())}, section=section))
    shared.opts.onchange("comfyui_reverse_proxy_enabled", update_reverse_proxy_enabled)
    update_reverse_proxy_enabled()


@ipc.restrict_to_process('webui')
def update_enabled():
    from modules import shared
    global_state.enabled = shared.opts.data.get('comfyui_enabled', True)


@ipc.restrict_to_process('webui')
def update_ipc_strategy():
    from modules import shared
    ipc_strategy_choice = shared.opts.data.get('comfyui_ipc_strategy', next(iter(ipc_strategy_choices.keys())))
    global_state.ipc_strategy_class = ipc_strategy_choices[ipc_strategy_choice]
    global_state.ipc_strategy_class_name = global_state.ipc_strategy_class.__name__


@ipc.restrict_to_process('webui')
def update_comfyui_graceful_termination_timeout():
    from modules import shared
    timeout = shared.opts.data.get('comfyui_graceful_termination_timeout', 5)
    global_state.comfyui_graceful_termination_timeout = timeout if timeout >= 0 else None


@ipc.restrict_to_process("webui")
def update_reverse_proxy_enabled():
    from modules import shared
    reverse_proxy_enabled = shared.opts.data.get('comfyui_reverse_proxy_enabled', next(iter(reverse_proxy_choices.keys())))
    global_state.reverse_proxy_enabled = reverse_proxy_choices[reverse_proxy_enabled]() and getattr(shared.cmd_opts, "api", False)


@ipc.restrict_to_process("webui")
def subscribe_update_button(component, **kwargs):
    if getattr(component, "elem_id", None) == "setting_comfyui_update_button":
        component.click(fn=update_comfyui)


@ipc.restrict_to_process("webui")
def update_comfyui():
    install_comfyui.update(get_install_location())


ipc_strategy_choices = {
    'Default': ipc.strategies.OsFriendlyIpcStrategy,
    'Shared memory': ipc.strategies.SharedMemoryIpcStrategy,
    'File system': ipc.strategies.FileSystemIpcStrategy,
}


ipc_display_names = {
    v.__name__: k
    for k, v in ipc_strategy_choices.items()
    if k != 'Default'
}


@ipc.restrict_to_process('webui')
def get_install_location() -> Path:
    from modules import shared
    install_location = install_comfyui.default_install_location
    install_location = shared.opts.data.get('comfyui_install_location', install_location).strip()
    return Path(install_location)


@ipc.restrict_to_process('webui')
def get_additional_argv():
    from modules import shared
    return [arg.strip() for arg in shared.opts.data.get('comfyui_additional_args', '').split()]


@ipc.restrict_to_process('webui')
def get_setting_value(setting_key):
    webui_argv = get_additional_argv()
    index = webui_argv.index(setting_key) if setting_key in webui_argv else -1
    setting_value = webui_argv[index + 1] if 0 <= index < len(webui_argv) - 1 else None
    return setting_value


@ipc.restrict_to_process('webui')
def get_comfyui_iframe_url():
    update_reverse_proxy_enabled()
    if global_state.reverse_proxy_enabled:
        return get_comfyui_reverse_proxy_url()
    else:
        return get_comfyui_client_url()


@ipc.restrict_to_process('webui')
def get_comfyui_reverse_proxy_url():
    """
    comfyui reverse proxy url, as seen from the browser
    """
    return get_comfyui_reverse_proxy_route()


def get_comfyui_reverse_proxy_route():
    return "/sd-webui-comfyui/comfyui"


@ipc.restrict_to_process('webui')
def get_comfyui_client_url():
    """
    comfyui server direct url, as seen from the browser
    """
    from modules import shared
    loopback_address = '127.0.0.1'
    server_url = "http://" + (get_setting_value('--listen') or getattr(shared.cmd_opts, 'comfyui_listen', loopback_address)) + ":" + str(get_port())
    client_url = shared.opts.data.get('comfyui_client_address', None) or getattr(shared.cmd_opts, 'webui_comfyui_client_address', None) or server_url
    if client_url.startswith(('http://0.0.0.0', 'https://0.0.0.0')):
        print(textwrap.dedent(f"""
            [sd-webui-comfyui] changing the ComfyUI client address from {client_url} to http://{loopback_address}
            This does not change the --listen address passed to ComfyUI, but instead the address used by the extension to load the iframe
            To override this behavior, navigate to the extension settings or use the --webui-comfyui-client-address <address> cli argument
        """), sys.stderr)
        client_url = client_url.replace("0.0.0.0", "127.0.0.1", 1)

    return client_url


@ipc.restrict_to_process('webui')
def get_comfyui_server_url():
    """
    comfyui server url, as seen from the webui server
    """
    return f"http://localhost:{get_port()}"


@ipc.restrict_to_process('webui')
def get_port():
    from modules import shared
    return get_setting_value('--port') or getattr(shared.cmd_opts, 'comfyui_port', 8188)


@ipc.restrict_to_process('webui')
def is_webui_server_remote():
    from modules import shared
    return any(
        bool(getattr(shared.cmd_opts, opt, False))
        for opt in (
            "share",
            "ngrok",

            # additional reverse proxy options from https://github.com/Bing-su/sd-webui-tunnels
            "cloudflared",
            "localhostrun",
            "remotemoe",
            "jprq",
            "bore",
            "googleusercontent",
            "tunnel-webhook",
        )
    )


reverse_proxy_choices = {
    "Default": is_webui_server_remote,
    "Always": lambda: True,
    "Never": lambda: False,
}


class WebuiOptions:
    def __getattr__(self, item):
        return WebuiOptions.opts_getattr(item)

    @staticmethod
    @ipc.run_in_process('webui')
    def opts_getattr(item):
        from modules import shared
        return getattr(shared.opts, item)


class WebuiSharedState:
    def __getattr__(self, item):
        return WebuiSharedState.shared_state_getattr(item)

    @staticmethod
    @ipc.run_in_process('webui')
    def shared_state_getattr(item):
        from modules import shared
        return getattr(shared.state, item)


opts = WebuiOptions()
shared_state = WebuiSharedState()


__base_dir = None


@ipc.run_in_process('webui')
def get_extension_base_dir():
    init_extension_base_dir()
    return __base_dir


@ipc.restrict_to_process('webui')
def init_extension_base_dir():
    global __base_dir
    from modules import scripts
    if __base_dir is None:
        __base_dir = scripts.basedir()
