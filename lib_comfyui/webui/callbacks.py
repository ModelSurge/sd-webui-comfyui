from lib_comfyui import comfyui_process, comfyui_context, ipc, global_state, external_code
from lib_comfyui.webui import tab, settings, workflow_patcher


@ipc.restrict_to_process('webui')
def register_callbacks():
    from modules import script_callbacks
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)
    script_callbacks.on_cfg_denoiser(on_cfg_denoiser)
    script_callbacks.on_cfg_denoised(on_cfg_denoised)


@ipc.restrict_to_process('webui')
def on_ui_tabs():
    return tab.create_tab()


@ipc.restrict_to_process('webui')
def on_ui_settings():
    return settings.create_section()


@ipc.restrict_to_process('webui')
def on_app_started(_gr_root, _fast_api):
    comfyui_process.start()


@ipc.restrict_to_process('webui')
def on_script_unloaded():
    comfyui_process.stop()
    workflow_patcher.clear_patches()
    global_state.is_ui_instantiated = False
    external_code.clear_workflow_types()


@ipc.restrict_to_process('webui')
def on_cfg_denoiser(params):
    workflow_patcher.before_unet(params)


@ipc.restrict_to_process('webui')
def on_cfg_denoised(params):
    workflow_patcher.after_unet(params)
