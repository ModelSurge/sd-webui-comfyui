from urllib.parse import urlparse, urlunparse

from lib_comfyui import comfyui_process, ipc, global_state, external_code
from lib_comfyui.webui import tab, settings, workflow_patcher, reverse_proxy
from websockets.exceptions import ConnectionClosedOK


@ipc.restrict_to_process('webui')
def register_callbacks():
    from modules import script_callbacks
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_after_component(on_after_component)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)


@ipc.restrict_to_process('webui')
def on_ui_tabs():
    return tab.create_tab()


@ipc.restrict_to_process('webui')
def on_ui_settings():
    return settings.create_section()


@ipc.restrict_to_process('webui')
def on_after_component(*args, **kwargs):
    return workflow_patcher.watch_prompts(*args, **kwargs)


@ipc.restrict_to_process('webui')
def on_app_started(_gr_root, fast_api):
    comfyui_process.start()
    reverse_proxy.register_comfyui(fast_api)


@ipc.restrict_to_process('webui')
def on_script_unloaded():
    comfyui_process.stop()
    workflow_patcher.clear_patches()
    global_state.is_ui_instantiated = False
    external_code.clear_workflow_types()
