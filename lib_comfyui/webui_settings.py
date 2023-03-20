from modules import shared
import importlib
import install_comfyui
importlib.reload(install_comfyui)


def create_section():
    section = ('comfy_ui', "ComfyUI")
    shared.opts.add_option("comfyui_install_location", shared.OptionInfo(
        install_comfyui.default_install_location, "ComfyUI install location", section=section))


def get_install_location():
    install_location = install_comfyui.default_install_location
    install_location = shared.opts.data.get('comfyui_install_location', install_location).strip()
    return install_location
