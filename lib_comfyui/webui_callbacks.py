import importlib
from modules import script_callbacks
from lib_comfyui import comfyui_adapter, comfyui_tab, comfyui_settings
importlib.reload(comfyui_adapter)
importlib.reload(comfyui_tab)
importlib.reload(comfyui_settings)


def on_ui_tabs():
    return comfyui_tab.generate_gradio_component()


def on_ui_settings():
    return comfyui_settings.add_settings()


def on_app_started(_gr_root, _fast_api):
    comfyui_adapter.start()


def on_script_unloaded():
    comfyui_adapter.stop()


def register_callbacks():
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)
