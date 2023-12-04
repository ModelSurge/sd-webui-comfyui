from modules.processing import StableDiffusionProcessingTxt2Img, StableDiffusionProcessingImg2Img
from lib_comfyui import comfyui_process, ipc, global_state, external_code, default_workflow_types
from lib_comfyui.webui import tab, settings, patches, reverse_proxy
from lib_comfyui.comfyui import type_conversion


@ipc.restrict_to_process('webui')
def register_callbacks():
    from modules import script_callbacks
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_after_component(on_after_component)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)
    script_callbacks.on_before_image_saved(on_before_image_saved)


@ipc.restrict_to_process('webui')
def on_ui_tabs():
    return tab.create_tab()


@ipc.restrict_to_process('webui')
def on_ui_settings():
    return settings.create_section()


@ipc.restrict_to_process('webui')
def on_after_component(*args, **kwargs):
    patches.watch_prompts(*args, **kwargs)
    settings.subscribe_update_button(*args, **kwargs)


@ipc.restrict_to_process('webui')
def on_app_started(_gr_root, fast_api):
    comfyui_process.start()
    reverse_proxy.create_comfyui_proxy(fast_api)


@ipc.restrict_to_process('webui')
def on_script_unloaded():
    comfyui_process.stop()
    patches.clear_patches()
    global_state.is_ui_instantiated = False
    external_code.clear_workflow_types()


@ipc.restrict_to_process('webui')
def on_before_image_saved(params):
    if isinstance(params.p, StableDiffusionProcessingTxt2Img):
        tab = 'txt2img'
    elif isinstance(params.p, StableDiffusionProcessingImg2Img):
        tab = 'img2img'
    else:
        return

    if not external_code.is_workflow_type_enabled(default_workflow_types.before_save_image_workflow_type.get_ids(tab)[0]):
        return

    results = external_code.run_workflow(
        workflow_type=default_workflow_types.before_save_image_workflow_type,
        tab=tab,
        batch_input=type_conversion.webui_image_to_comfyui([params.image]),
        identity_on_error=True,
    )

    params.image = type_conversion.comfyui_image_to_webui(results[0], return_tensors=False)[0]
