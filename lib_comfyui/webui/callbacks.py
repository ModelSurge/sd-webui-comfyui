from lib_comfyui import comfyui_process, ipc, comfyui_context
from lib_comfyui.webui import tab, settings, workflow_patcher


def on_ui_tabs():
    return tab.create_tab()


def on_ui_settings():
    return settings.create_section()


def on_app_started(_gr_root, _fast_api):
    comfyui_process.start()


def on_script_unloaded():
    comfyui_process.stop()
    workflow_patcher.clear_patches()


@ipc.restrict_to_process('webui')
def register_callbacks():
    from modules import script_callbacks
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)
