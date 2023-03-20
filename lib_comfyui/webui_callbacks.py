import importlib
import os.path

from modules import script_callbacks
from lib_comfyui import comfyui_adapter, webui_tab, webui_settings
importlib.reload(comfyui_adapter)
importlib.reload(webui_tab)
importlib.reload(webui_settings)


def on_ui_tabs():
    return webui_tab.create_tab()


def on_ui_settings():
    return webui_settings.create_section()


def on_app_started(_gr_root, _fast_api):
    comfyui_adapter.start()


def on_script_unloaded():
    comfyui_adapter.stop()


def register_callbacks():
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)
