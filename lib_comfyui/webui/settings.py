import sys
import textwrap
from lib_comfyui import ipc, global_state, ipc_strategies
import install_comfyui


@ipc.restrict_to_process('webui')
def create_section():
    from modules import shared
    import gradio as gr

    section = ('comfyui', "ComfyUI")
    shared.opts.add_option('comfyui_enabled', shared.OptionInfo(True, 'Enable sd-webui-comfyui extension', section=section))
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


ipc_strategy_choices = {
    'Default': ipc_strategies.OsFriendlyIpcStrategy,
    'Shared memory': ipc_strategies.SharedMemoryIpcStrategy,
    'File system': ipc_strategies.FileSystemIpcStrategy,
}


ipc_display_names = {
    v.__name__: k
    for k, v in ipc_strategy_choices.items()
    if k != 'Default'
}


@ipc.restrict_to_process('webui')
def get_install_location():
    from modules import shared
    install_location = install_comfyui.default_install_location
    install_location = shared.opts.data.get('comfyui_install_location', install_location).strip()
    return install_location


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
def get_port():
    from modules import shared
    return get_setting_value('--port') or getattr(shared.cmd_opts, 'comfyui_port', 8188)


@ipc.restrict_to_process('webui')
def get_comfyui_client_url():
    from modules import shared
    loopback_address = '127.0.0.1'
    server_url = get_setting_value('--listen') or getattr(shared.cmd_opts, 'comfyui_listen', loopback_address)
    client_url = shared.opts.data.get('comfyui_client_address', None) or getattr(shared.cmd_opts, 'webui_comfyui_client_address', None) or server_url
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
from lib_comfyui import ipc


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
